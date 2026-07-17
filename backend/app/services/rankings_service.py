import re
import asyncio
from datetime import datetime, timezone
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.team import Team
from ..models.game import Game
from ..models.ai_top25 import AiTop25Ranking
from ..config import settings
from .cfbd_client import cfbd

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

AP_POLL_NAME = "AP Top 25"


async def _resolve_game_season(db: AsyncSession) -> int | None:
    return (await db.execute(select(func.max(Game.season)))).scalar()


async def list_ranking_weeks(db: AsyncSession, season: int | None = None) -> dict:
    if season is None:
        season = await _resolve_game_season(db)
        if season is None:
            return {"season": None, "weeks": []}
    result = await db.execute(select(Game.week).where(Game.season == season).distinct().order_by(Game.week))
    weeks = [w for (w,) in result.all() if w is not None]
    return {"season": season, "weeks": weeks}


async def get_ap_poll(db: AsyncSession, season: int | None = None, week: int | None = None) -> dict:
    """Real AP Top 25 (the poll ESPN reports). Live-fetched from CFBD, not stored —
    same pattern as SP+/advanced stats. If no specific week is requested, walks
    backward through real weeks to find the most recent poll that's been released."""
    if season is None:
        season = await _resolve_game_season(db)
        if season is None:
            return {"season": None, "week": None, "rankings": []}

    if week is not None:
        weeks_to_try = [week]
    else:
        weeks_info = await list_ranking_weeks(db, season)
        weeks_to_try = list(reversed(weeks_info["weeks"])) or [1]

    for wk in weeks_to_try:
        try:
            data = await cfbd.rankings(season, week=wk)
        except Exception:
            continue
        if not data:
            continue
        polls = data[0].get("polls", [])
        ap = next((p for p in polls if p.get("poll") == AP_POLL_NAME), None)
        if ap and ap.get("ranks"):
            return {
                "season": season,
                "week": data[0].get("week", wk),
                "rankings": [
                    {
                        "rank": r["rank"], "school": r["school"], "conference": r.get("conference"),
                        "first_place_votes": r.get("firstPlaceVotes"), "points": r.get("points"),
                    }
                    for r in ap["ranks"]
                ],
            }

    return {"season": season, "week": week, "rankings": []}


async def _team_summary_lines(db: AsyncSession, season: int) -> list[str]:
    result = await db.execute(select(Team).where(Team.season == season, Team.classification == "fbs"))
    current_teams = {t.school: t for t in result.scalars().all()}

    result = await db.execute(select(Team).where(Team.season == season - 1))
    last_teams = {t.school: t for t in result.scalars().all()}

    result = await db.execute(select(Game).where(Game.season == season, Game.completed.is_(True)))
    record_so_far: dict[str, list[int]] = {}
    for g in result.scalars().all():
        for team, pts, opp_pts in [(g.home_team, g.home_points, g.away_points), (g.away_team, g.away_points, g.home_points)]:
            if team not in current_teams or pts is None or opp_pts is None:
                continue
            rec = record_so_far.setdefault(team, [0, 0])
            rec[0 if pts > opp_pts else 1] += 1

    sp_by_team = {}
    try:
        sp_data = await cfbd.sp_ratings(season)
        if not sp_data:
            sp_data = await cfbd.sp_ratings(season - 1)
        sp_by_team = {r["team"]: r for r in sp_data}
    except Exception:
        pass

    lines = []
    for school, t in current_teams.items():
        bits = [f"{school} ({t.conference or 'Independent'})"]
        rec = record_so_far.get(school)
        if rec:
            bits.append(f"{rec[0]}-{rec[1]} so far this season")
        last = last_teams.get(school)
        if last:
            bits.append(f"{last.wins or 0}-{last.losses or 0} last season")
        sp = sp_by_team.get(school)
        if sp and sp.get("rating") is not None:
            bits.append(f"SP+ {sp['rating']:.1f}")
        lines.append(" — ".join(bits))
    return lines


async def get_cached_ai_top25(db: AsyncSession, season: int | None = None) -> dict | None:
    if season is None:
        season = await _resolve_game_season(db)
        if season is None:
            return None
    result = await db.execute(
        select(AiTop25Ranking).where(AiTop25Ranking.season == season).order_by(AiTop25Ranking.generated_at.desc())
    )
    entry = result.scalars().first()
    if not entry:
        return None
    return {
        "season": entry.season, "generated_at": entry.generated_at.isoformat(),
        "rankings": entry.rankings, "methodology": entry.methodology,
    }


async def generate_ai_top25(db: AsyncSession, season: int | None = None) -> dict | None:
    if season is None:
        season = await _resolve_game_season(db)
        if season is None:
            return None

    lines = await _team_summary_lines(db, season)
    if not lines:
        return None
    context = "\n".join(lines)

    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=2200,
        system=(
            "You are a college football analyst producing your own AI Top 25 rankings, independent of "
            "the official AP/Coaches polls. Base your rankings on the signals given per team: SP+ rating "
            "(advanced efficiency metric — the single best indicator of team quality here), this season's "
            "record so far if any games have been played, and last season's record for continuity/context. "
            "If this season hasn't started yet, this is a preseason projection — weight SP+ and last "
            "season's performance most heavily and say so. Respond with EXACTLY 25 lines, one per team, "
            "in this exact format and nothing else:\n"
            "RANK. Team Name — one-sentence justification citing specific numbers given\n"
            "Example: 1. Ohio State — Elite returning production and the nation's best SP+ rating at 32.1."
        ),
        messages=[{"role": "user", "content": f"Rank the top 25 teams from this list of every FBS team:\n\n{context}"}],
    )
    text = response.content[0].text

    rankings = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\.\s*(.+?)\s*[—-]\s*(.+)", line)
        if m:
            rankings.append({"rank": int(m.group(1)), "school": m.group(2).strip(), "blurb": m.group(3).strip()})

    if not rankings:
        return None

    generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    entry = AiTop25Ranking(
        season=season, generated_at=generated_at, rankings=rankings,
        methodology="SP+ rating, in-season record, and prior-season record",
    )
    db.add(entry)
    await db.commit()
    return {"season": season, "generated_at": generated_at.isoformat(), "rankings": rankings, "methodology": entry.methodology}
