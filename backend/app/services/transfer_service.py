import asyncio
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.transfer import TransferPortalEntry
from ..models.team import Team
from ..config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# Approximate composite-rating point value for entries CFBD didn't give a numeric `rating` for.
STAR_POINTS = {5: 0.98, 4: 0.91, 3: 0.84, 2: 0.78, 1: 0.72}
DEFAULT_POINTS = 0.70


def _point_value(rating: float | None, stars: int | None) -> float:
    if rating:
        return rating
    return STAR_POINTS.get(stars, DEFAULT_POINTS)


def _entry_dict(e: TransferPortalEntry) -> dict:
    return {
        "id": e.id,
        "player_name": e.player_name,
        "position": e.position,
        "from_school": e.from_school,
        "to_school": e.to_school,
        "season": e.season,
        "class_year": e.year_in_school,
        "eligibility_status": e.eligibility_status,
        "stars": e.stars,
        "rating": e.rating,
        "committed": e.committed,
        "entered_date": e.entered_date.isoformat() if e.entered_date else None,
        "overall_grade": e.overall_grade,
        "ai_analysis": e.ai_analysis,
    }


async def _resolve_portal_season(db: AsyncSession) -> int | None:
    return (await db.execute(select(func.max(TransferPortalEntry.season)))).scalar()


async def list_portal_entries(
    db: AsyncSession,
    season: int | None = None,
    position: str | None = None,
    from_school: str | None = None,
    to_school: str | None = None,
    committed: bool | None = None,
    limit: int = 200,
) -> list[dict]:
    if season is None:
        season = await _resolve_portal_season(db)
        if season is None:
            return []

    query = select(TransferPortalEntry).where(TransferPortalEntry.season == season)
    if position:
        query = query.where(TransferPortalEntry.position == position)
    if from_school:
        query = query.where(TransferPortalEntry.from_school == from_school)
    if to_school:
        query = query.where(TransferPortalEntry.to_school == to_school)
    if committed is not None:
        query = query.where(TransferPortalEntry.committed == committed)
    query = query.order_by(TransferPortalEntry.entered_date.desc().nullslast()).limit(limit)
    result = await db.execute(query)
    return [_entry_dict(e) for e in result.scalars().all()]


async def get_team_portal_activity(db: AsyncSession, school: str, season: int | None = None) -> dict:
    """Who a team lost and gained this transfer cycle."""
    if season is None:
        season = await _resolve_portal_season(db)
        if season is None:
            return {"season": None, "lost": [], "gained": []}

    lost = (await db.execute(
        select(TransferPortalEntry).where(TransferPortalEntry.season == season, TransferPortalEntry.from_school == school)
    )).scalars().all()
    gained = (await db.execute(
        select(TransferPortalEntry).where(
            TransferPortalEntry.season == season,
            TransferPortalEntry.to_school == school,
            TransferPortalEntry.committed.is_(True),
        )
    )).scalars().all()

    return {
        "season": season,
        "lost": [_entry_dict(e) for e in lost],
        "gained": [_entry_dict(e) for e in gained],
    }


async def get_portal_rankings(db: AsyncSession, season: int | None = None, conference: str | None = None) -> dict:
    """Rank teams on their transfer portal class — primarily by the composite
    value of talent they added (the standard 'who won the portal' metric),
    with net gain/loss and raw counts shown alongside for context."""
    if season is None:
        season = await _resolve_portal_season(db)
        if season is None:
            return {"season": None, "conference": conference, "rankings": []}

    team_season = (await db.execute(select(func.max(Team.season)))).scalar()
    team_query = select(Team.school, Team.conference).where(Team.season == team_season)
    if conference:
        team_query = team_query.where(Team.conference == conference)
    team_rows = (await db.execute(team_query)).all()
    conference_by_school = {school: conf for school, conf in team_rows}

    entries = (await db.execute(
        select(TransferPortalEntry).where(TransferPortalEntry.season == season)
    )).scalars().all()

    stats: dict[str, dict] = {}

    def _bucket(school: str) -> dict:
        return stats.setdefault(school, {
            "incoming_score": 0.0, "outgoing_score": 0.0,
            "incoming_count": 0, "outgoing_count": 0,
        })

    for e in entries:
        pts = _point_value(e.rating, e.stars)
        if e.committed and e.to_school in conference_by_school:
            b = _bucket(e.to_school)
            b["incoming_score"] += pts
            b["incoming_count"] += 1
        if e.from_school in conference_by_school:
            b = _bucket(e.from_school)
            b["outgoing_score"] += pts
            b["outgoing_count"] += 1

    rankings = []
    for school, s in stats.items():
        rankings.append({
            "school": school,
            "conference": conference_by_school.get(school),
            "incoming_score": round(s["incoming_score"], 2),
            "outgoing_score": round(s["outgoing_score"], 2),
            "net_score": round(s["incoming_score"] - s["outgoing_score"], 2),
            "incoming_count": s["incoming_count"],
            "outgoing_count": s["outgoing_count"],
        })
    rankings.sort(key=lambda r: r["incoming_score"], reverse=True)
    for i, r in enumerate(rankings, start=1):
        r["rank"] = i

    return {"season": season, "conference": conference, "rankings": rankings}


async def grade_portal_entry(db: AsyncSession, entry_id: int) -> TransferPortalEntry | None:
    result = await db.execute(select(TransferPortalEntry).where(TransferPortalEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        return None

    context = (
        f"Name: {entry.player_name}\nPosition: {entry.position}\n"
        f"From: {entry.from_school}\nTo: {entry.to_school or 'Uncommitted'}\n"
        f"Class: {entry.year_in_school}\nStars: {entry.stars}\nRating: {entry.rating}"
    )
    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=(
            "You are a college football transfer portal analyst. Grade this transfer 0-100 "
            "and give a 2-3 sentence analysis of the move and fit. "
            "Respond in the format: GRADE: <number>\\nANALYSIS: <text>"
        ),
        messages=[{"role": "user", "content": f"Grade this transfer portal move:\n\n{context}"}],
    )
    text = response.content[0].text
    grade = None
    analysis = text
    for line in text.splitlines():
        if line.upper().startswith("GRADE:"):
            try:
                grade = int("".join(c for c in line.split(":", 1)[1] if c.isdigit()))
            except ValueError:
                pass
        elif line.upper().startswith("ANALYSIS:"):
            analysis = line.split(":", 1)[1].strip()

    entry.overall_grade = grade
    entry.ai_analysis = analysis
    await db.commit()
    return entry
