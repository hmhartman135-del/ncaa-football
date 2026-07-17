from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from ..models.recruit import Recruit
from ..models.team import Team
from ..models.recruit_team_ranking import Recruit247TeamRanking
from .transfer_service import _point_value


def _recruit_dict(r: Recruit) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "position": r.position,
        "class_year": r.class_year,
        "stars": r.stars,
        "rating": r.rating,
        "national_rank": r.national_rank,
        "position_rank": r.position_rank,
        "state_rank": r.state_rank,
        "height": r.height,
        "weight": r.weight,
        "city": r.city,
        "state_province": r.state_province,
        "committed_to": r.committed_to,
        "committed": r.committed,
        "source": r.source,
        "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
    }


async def _resolve_recruiting_class(db: AsyncSession) -> int | None:
    return (await db.execute(select(func.max(Recruit.class_year)))).scalar()


async def list_recruits(
    db: AsyncSession,
    class_year: int | None = None,
    position: str | None = None,
    committed_to: str | None = None,
    min_stars: int | None = None,
    limit: int = 200,
) -> list[dict]:
    if class_year is None:
        class_year = await _resolve_recruiting_class(db)
        if class_year is None:
            return []

    query = select(Recruit).where(Recruit.class_year == class_year)
    if position:
        query = query.where(Recruit.position == position)
    if committed_to:
        query = query.where(Recruit.committed_to == committed_to)
    if min_stars:
        query = query.where(Recruit.stars >= min_stars)
    query = query.order_by(Recruit.national_rank.asc().nulls_last()).limit(limit)
    result = await db.execute(query)
    return [_recruit_dict(r) for r in result.scalars().all()]


async def get_team_recruits(db: AsyncSession, school: str, class_year: int | None = None) -> dict:
    if class_year is None:
        class_year = await _resolve_recruiting_class(db)
        if class_year is None:
            return {"class_year": None, "recruits": []}

    result = await db.execute(
        select(Recruit)
        .where(Recruit.class_year == class_year, Recruit.committed_to == school, Recruit.committed.is_(True))
        .order_by(Recruit.national_rank.asc().nulls_last())
    )
    recruits = result.scalars().all()
    return {
        "class_year": class_year,
        "recruits": [_recruit_dict(r) for r in recruits],
        "average_rating": round(sum((r.rating or 0) for r in recruits) / len(recruits), 3) if recruits else None,
    }


async def get_recruiting_rankings(db: AsyncSession, class_year: int | None = None, conference: str | None = None) -> dict:
    """Team recruiting class rankings — sum of composite rating for all committed
    recruits (the standard 247/On3/Rivals methodology for 'who's winning recruiting')."""
    if class_year is None:
        class_year = await _resolve_recruiting_class(db)
        if class_year is None:
            return {"class_year": None, "conference": conference, "rankings": []}

    team_season = (await db.execute(select(func.max(Team.season)))).scalar()
    team_query = select(Team.school, Team.conference).where(Team.season == team_season)
    if conference:
        team_query = team_query.where(Team.conference == conference)
    conference_by_school = {school: conf for school, conf in (await db.execute(team_query)).all()}

    recruits = (await db.execute(
        select(Recruit).where(Recruit.class_year == class_year, Recruit.committed.is_(True))
    )).scalars().all()

    stats: dict[str, dict] = {}
    for r in recruits:
        if r.committed_to not in conference_by_school:
            continue
        b = stats.setdefault(r.committed_to, {"score": 0.0, "count": 0, "five_star": 0, "four_star": 0, "three_star": 0})
        b["score"] += _point_value(r.rating, r.stars)
        b["count"] += 1
        if r.stars == 5:
            b["five_star"] += 1
        elif r.stars == 4:
            b["four_star"] += 1
        elif r.stars == 3:
            b["three_star"] += 1

    rankings = []
    for school, s in stats.items():
        rankings.append({
            "school": school,
            "conference": conference_by_school.get(school),
            "score": round(s["score"], 2),
            "count": s["count"],
            "average_rating": round(s["score"] / s["count"], 3) if s["count"] else None,
            "five_star": s["five_star"],
            "four_star": s["four_star"],
            "three_star": s["three_star"],
        })
    rankings.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rankings, start=1):
        r["rank"] = i

    return {"class_year": class_year, "conference": conference, "rankings": rankings}


async def save_247_recruits(db: AsyncSession, class_year: int, rows: list[dict]) -> int:
    """Replace the stored 247Sports player-ranking snapshot for a class year.
    `rows` are dicts matching the Recruit columns (name/position/stars/rating/
    national_rank/position_rank/state_rank/city/state_province/committed_to/
    committed), as pulled directly off a 247Sports.com recruit-rankings page
    the user linked. Only replaces rows previously tagged source='247sports'
    for this class year — leaves any CFBD-sourced rows for the same class
    year untouched."""
    await db.execute(
        delete(Recruit).where(Recruit.class_year == class_year, Recruit.source == "247sports")
    )
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        db.add(Recruit(
            class_year=class_year,
            name=row["name"],
            position=row.get("position"),
            stars=row.get("stars"),
            rating=row.get("rating"),
            national_rank=row.get("national_rank"),
            position_rank=row.get("position_rank"),
            state_rank=row.get("state_rank"),
            height=row.get("height"),
            weight=row.get("weight"),
            city=row.get("city"),
            state_province=row.get("state_province"),
            committed_to=row.get("committed_to"),
            committed=row.get("committed", False),
            source="247sports",
            fetched_at=fetched_at,
        ))
    await db.commit()
    return len(rows)


async def save_247_team_rankings(db: AsyncSession, class_year: int, rows: list[dict]) -> int:
    """Replace the stored 247Sports team-ranking snapshot for a class year.
    `rows` are dicts with rank/school/commits/avg_rating/points, as pulled
    directly off a 247Sports.com rankings page the user linked."""
    await db.execute(delete(Recruit247TeamRanking).where(Recruit247TeamRanking.class_year == class_year))
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        db.add(Recruit247TeamRanking(
            class_year=class_year,
            rank=row["rank"],
            school=row["school"],
            commits=row.get("commits"),
            avg_rating=row.get("avg_rating"),
            points=row.get("points"),
            fetched_at=fetched_at,
        ))
    await db.commit()
    return len(rows)


async def get_247_team_rankings(db: AsyncSession, class_year: int | None = None, conference: str | None = None) -> dict:
    """Real 247Sports team recruiting rankings — manually snapshotted (see
    save_247_team_rankings), not auto-refreshed. Falls back to nothing (empty
    list) if we've never been given a snapshot for this class year."""
    if class_year is None:
        class_year = (await db.execute(select(func.max(Recruit247TeamRanking.class_year)))).scalar()
        if class_year is None:
            return {"class_year": None, "conference": conference, "fetched_at": None, "rankings": []}

    team_season = (await db.execute(select(func.max(Team.season)))).scalar()
    conference_by_school = {
        school: conf for school, conf in
        (await db.execute(select(Team.school, Team.conference).where(Team.season == team_season))).all()
    }

    result = await db.execute(
        select(Recruit247TeamRanking)
        .where(Recruit247TeamRanking.class_year == class_year)
        .order_by(Recruit247TeamRanking.rank.asc())
    )
    rows = result.scalars().all()
    fetched_at = rows[0].fetched_at.isoformat() if rows else None

    rankings = []
    for r in rows:
        conf = conference_by_school.get(r.school)
        if conference and conf != conference:
            continue
        rankings.append({
            "rank": r.rank, "school": r.school, "conference": conf,
            "commits": r.commits, "avg_rating": r.avg_rating, "points": r.points,
        })

    return {"class_year": class_year, "conference": conference, "fetched_at": fetched_at, "rankings": rankings}
