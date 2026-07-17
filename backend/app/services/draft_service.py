import asyncio
import re
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.player import Player, PlayerSeasonStats
from ..models.draft import DraftProspect
from ..models.team import Team
from ..models.transfer import TransferPortalEntry
from ..config import settings
from .roster_service import _drafted_players

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

CLASS_LABELS = {"3": "Junior", "JR": "Junior", "4": "Senior", "SR": "Senior", "5": "Grad", "GR": "Grad"}


async def list_draft_eligible(db: AsyncSession, season: int | None = None, position: str | None = None, limit: int = 100):
    """Real draft-eligible players (JR/SR/GR) for the *next* draft. Excludes
    anyone already taken in the most recent actual NFL Draft — they're not
    eligible for the next one.

    Ranking: raw PPA total isn't comparable across positions (a QB touches
    nearly every offensive snap, so QBs' PPA totals dwarf every other
    position's — sorting the whole board by raw PPA returns an all-QB list).
    When no position filter is given, players are instead ranked by their
    percentile *within their own position group* (1.0 = best at their
    position, ~0 = worst), so the combined board is an actual mix of
    positions. A single-position filter just sorts that group by raw PPA,
    where the comparison is apples-to-apples.

    Also restricted to FBS teams — FCS competition is weak enough that raw
    production stats there aren't comparable to FBS (an FCS player's PPA can
    look elite purely because of the level of defense they're facing), and
    the NFL Draft is overwhelmingly drawn from FBS anyway. Uses `Team.classification`
    (real ingested data), not a guess."""
    if season is None:
        season = (await db.execute(select(func.max(Player.season)))).scalar()
        if season is None:
            return []

    drafted_ids, drafted_names = await _drafted_players(db)

    portal_cycle = (await db.execute(select(func.max(TransferPortalEntry.season)))).scalar()
    current_team_by_name: dict[str, str] = {}
    if portal_cycle is not None:
        result = await db.execute(
            select(TransferPortalEntry.player_name, TransferPortalEntry.to_school).where(
                TransferPortalEntry.season == portal_cycle, TransferPortalEntry.committed.is_(True)
            )
        )
        current_team_by_name = {name: to_school for name, to_school in result.all()}

    team_season = (await db.execute(select(func.max(Team.season)))).scalar()
    fbs_schools = {
        school for (school,) in (await db.execute(
            select(Team.school).where(Team.season == team_season, Team.classification == "fbs")
        )).all()
    }

    query = (
        select(Player, PlayerSeasonStats)
        .outerjoin(
            PlayerSeasonStats,
            (Player.id == PlayerSeasonStats.player_id) & (PlayerSeasonStats.season == season),
        )
        .where(Player.season == season, Player.draft_eligible.is_(True))
    )
    if position:
        query = query.where(Player.position == position)
    result = await db.execute(query)
    rows = [
        (player, stats) for player, stats in result.all()
        if not ((player.cfbd_id and player.cfbd_id in drafted_ids) or player.name in drafted_names)
        and player.team in fbs_schools
    ]

    if position:
        rows.sort(key=lambda ps: ps[1].ppa_total if ps[1] and ps[1].ppa_total is not None else float("-inf"), reverse=True)
        rows = rows[:limit]
    else:
        by_position: dict[str, list] = {}
        for player, stats in rows:
            by_position.setdefault(player.position, []).append((player, stats))

        scored, unscored = [], []
        for group in by_position.values():
            with_ppa = [(p, s) for p, s in group if s and s.ppa_total is not None]
            with_ppa.sort(key=lambda ps: ps[1].ppa_total, reverse=True)
            n = len(with_ppa)
            for i, (p, s) in enumerate(with_ppa):
                percentile = 1.0 if n == 1 else 1 - (i / (n - 1))
                scored.append((percentile, p, s))
            unscored.extend((p, s) for p, s in group if not (s and s.ppa_total is not None))

        scored.sort(key=lambda row: row[0], reverse=True)
        rows = [(p, s) for _, p, s in scored] + unscored
        rows = rows[:limit]

    return [
        {
            "player_id": player.id,
            "name": player.name,
            "position": player.position,
            "college": current_team_by_name.get(player.name, player.team),
            "former_college": player.team if player.name in current_team_by_name and current_team_by_name[player.name] != player.team else None,
            "class_year": CLASS_LABELS.get(str(player.year), player.year),
            "ppa_total": stats.ppa_total if stats else None,
            "games": stats.games if stats else None,
        }
        for player, stats in rows
    ]


async def get_or_create_prospect_grade(db: AsyncSession, player_id: int, draft_year: int = 2027) -> DraftProspect | None:
    existing = await db.execute(
        select(DraftProspect).where(DraftProspect.player_id == player_id, DraftProspect.draft_year == draft_year)
    )
    prospect = existing.scalar_one_or_none()
    if prospect:
        return prospect

    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        return None

    stats_result = await db.execute(
        select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == player_id)
    )
    stats = stats_result.scalar_one_or_none()

    stat_lines = []
    if stats:
        for field in [
            "games", "passing_yards", "passing_tds", "rushing_yards", "rushing_tds",
            "receiving_yards", "receiving_tds", "tackles", "sacks", "interceptions_def", "ppa_total",
        ]:
            val = getattr(stats, field, None)
            if val:
                stat_lines.append(f"{field}: {val}")
    stats_block = "\n".join(stat_lines) or "No stats recorded."

    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=900,
        system=(
            "You are an NFL draft analyst evaluating a real college football player for the "
            f"{draft_year} NFL Draft. Respond in this exact format:\n"
            "ROUND: <integer 1-7>\n"
            "GRADE: <letter grade, e.g. B+>\n"
            "COMP: <one NFL player comparison>\n"
            "ANALYSIS: <200-300 word scouting report covering strengths, weaknesses, and NFL projection>"
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Evaluate this {draft_year} NFL Draft prospect:\n"
                f"Name: {player.name}\nPosition: {player.position}\nCollege: {player.team}\n"
                f"Class: {CLASS_LABELS.get(str(player.year), player.year)}\n\nStats:\n{stats_block}"
            ),
        }],
    )
    text = response.content[0].text

    round_match = re.search(r"ROUND:\s*(\d+)", text)
    grade_match = re.search(r"GRADE:\s*([A-F][+-]?)", text)
    comp_match = re.search(r"COMP:\s*(.+)", text)
    analysis_match = re.search(r"ANALYSIS:\s*([\s\S]+)", text)

    prospect = DraftProspect(
        player_id=player.id,
        name=player.name,
        position=player.position,
        college=player.team,
        class_year=CLASS_LABELS.get(str(player.year), player.year),
        draft_year=draft_year,
        projected_round=int(round_match.group(1)) if round_match else None,
        grade=grade_match.group(1) if grade_match else None,
        nfl_comparison=comp_match.group(1).strip() if comp_match else None,
        ai_analysis=analysis_match.group(1).strip() if analysis_match else text,
    )
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)
    return prospect


async def get_draft_board(db: AsyncSession, draft_year: int = 2027, limit: int = 100):
    query = (
        select(DraftProspect)
        .where(DraftProspect.draft_year == draft_year)
        .order_by(DraftProspect.projected_round.asc().nulls_last())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()
