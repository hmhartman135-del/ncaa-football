import asyncio
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.player import Player, PlayerSeasonStats
from ..models.recruit import Recruit
from ..models.transfer import TransferPortalEntry
from ..models.nfl_draft_pick import NflDraftPick
from ..config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def _resolve_season(db: AsyncSession, team: str) -> int | None:
    """Latest season we actually have roster data for (CFBD doesn't publish
    a season's roster until close to kickoff, so this may lag the current year)."""
    result = await db.execute(select(func.max(Player.season)).where(Player.team == team))
    return result.scalar()


async def get_team_roster(db: AsyncSession, team: str, season: int | None = None):
    if season is None:
        season = await _resolve_season(db, team)
        if season is None:
            return {}

    result = await db.execute(
        select(Player, PlayerSeasonStats)
        .outerjoin(
            PlayerSeasonStats,
            (Player.id == PlayerSeasonStats.player_id) & (PlayerSeasonStats.season == season),
        )
        .where(Player.team == team, Player.season == season)
        .order_by(Player.position, Player.name)
    )
    rows = result.all()

    roster: dict[str, list[dict]] = {}
    for player, stats in rows:
        pos = player.position or "OTHER"
        roster.setdefault(pos, []).append({
            "id": player.id,
            "name": player.name,
            "position": pos,
            "year": player.year,
            "jersey": player.jersey,
            "height": player.height,
            "weight": player.weight,
            "games": stats.games if stats else 0,
        })
    return roster


EXHAUSTED_ELIGIBILITY_YEARS = {"4"}  # 4th-year player in the base season has no seasons left, absent a redshirt/medical year we have no data to detect


async def _current_team_overrides(db: AsyncSession) -> dict[str, str]:
    """Player name -> current committed transfer destination, for the latest
    portal cycle. Anything keyed off a Player row's static roster-season
    `team` field goes stale the moment someone transfers — this is the single
    source of truth for "where are they actually playing now" used across
    the roster, players list, and player-profile display."""
    portal_cycle = (await db.execute(select(func.max(TransferPortalEntry.season)))).scalar()
    if portal_cycle is None:
        return {}
    result = await db.execute(
        select(TransferPortalEntry.player_name, TransferPortalEntry.to_school).where(
            TransferPortalEntry.season == portal_cycle, TransferPortalEntry.committed.is_(True)
        )
    )
    return {name: to_school for name, to_school in result.all() if to_school}


async def _drafted_players(db: AsyncSession) -> tuple[set[int], set[str]]:
    """Players taken in the most recent NFL draft — matched by CFBD athlete id
    where available, falling back to exact name for picks missing that id."""
    draft_year = (await db.execute(select(func.max(NflDraftPick.draft_year)))).scalar()
    if draft_year is None:
        return set(), set()
    result = await db.execute(
        select(NflDraftPick.cfbd_athlete_id, NflDraftPick.name).where(NflDraftPick.draft_year == draft_year)
    )
    ids, names = set(), set()
    for athlete_id, name in result.all():
        if athlete_id:
            ids.add(athlete_id)
        else:
            names.add(name)
    return ids, names


async def _excluded_from_roster(db: AsyncSession, team: str) -> tuple[set[str], set[int], set[str]]:
    """(departed_names, drafted_ids, drafted_names) — anyone who left `team`
    via the latest transfer-portal cycle, plus anyone drafted, for filtering
    a team's real *current* player set. Shared by the roster, team analytics,
    and best-players views so they can't drift out of sync with each other."""
    portal_cycle = (await db.execute(select(func.max(TransferPortalEntry.season)))).scalar()
    departed_names: set[str] = set()
    if portal_cycle is not None:
        result = await db.execute(
            select(TransferPortalEntry.player_name)
            .where(TransferPortalEntry.season == portal_cycle, TransferPortalEntry.from_school == team)
        )
        departed_names = {name for (name,) in result.all()}
    drafted_ids, drafted_names = await _drafted_players(db)
    return departed_names, drafted_ids, drafted_names


async def get_current_roster(db: AsyncSession, team: str) -> dict:
    """Best real approximation of a team's *current* roster: last known full
    roster snapshot, adjusted for this cycle's actual transfer-portal
    departures/arrivals and signed recruits — since CFBD doesn't publish a
    fresh full roster until fall camp."""
    base_season = await _resolve_season(db, team)
    base_rows = []
    if base_season is not None:
        result = await db.execute(
            select(Player, PlayerSeasonStats)
            .outerjoin(
                PlayerSeasonStats,
                (Player.id == PlayerSeasonStats.player_id) & (PlayerSeasonStats.season == base_season),
            )
            .where(Player.team == team, Player.season == base_season)
        )
        base_rows = result.all()

    portal_cycle = (await db.execute(select(func.max(TransferPortalEntry.season)))).scalar()
    departed_names, drafted_ids, drafted_names = await _excluded_from_roster(db, team)
    incoming_transfers = []
    if portal_cycle is not None:
        result = await db.execute(
            select(TransferPortalEntry).where(
                TransferPortalEntry.season == portal_cycle,
                TransferPortalEntry.to_school == team,
                TransferPortalEntry.committed.is_(True),
            )
        )
        incoming_transfers = result.scalars().all()

    recruiting_class = (await db.execute(select(func.max(Recruit.class_year)))).scalar()
    incoming_signees = []
    if recruiting_class is not None:
        result = await db.execute(
            select(Recruit).where(
                Recruit.class_year == recruiting_class,
                Recruit.committed_to == team,
                Recruit.committed.is_(True),
            )
        )
        incoming_signees = result.scalars().all()

    roster: dict[str, list[dict]] = {}

    for player, stats in base_rows:
        if player.name in departed_names:
            continue
        if player.year in EXHAUSTED_ELIGIBILITY_YEARS:
            continue
        if (player.cfbd_id and player.cfbd_id in drafted_ids) or player.name in drafted_names:
            continue
        pos = player.position or "OTHER"
        roster.setdefault(pos, []).append({
            "id": player.id,
            "name": player.name,
            "position": pos,
            "year": player.year,
            "jersey": player.jersey,
            "height": player.height,
            "weight": player.weight,
            "games": stats.games if stats else 0,
            "status": "returning",
        })

    for t in incoming_transfers:
        pos = t.position or "OTHER"
        roster.setdefault(pos, []).append({
            "id": f"transfer-{t.id}",
            "name": t.player_name,
            "position": pos,
            "year": t.year_in_school,
            "jersey": None,
            "height": None,
            "weight": None,
            "games": None,
            "status": "transfer in",
            "from_school": t.from_school,
        })

    for r in incoming_signees:
        pos = r.position or "OTHER"
        roster.setdefault(pos, []).append({
            "id": f"signee-{r.id}",
            "name": r.name,
            "position": pos,
            "year": "HS",
            "jersey": None,
            "height": r.height,
            "weight": r.weight,
            "games": None,
            "status": "signee",
            "stars": r.stars,
        })

    for players in roster.values():
        players.sort(key=lambda p: p["name"])

    return {
        "base_season": base_season,
        "portal_cycle": portal_cycle,
        "recruiting_class": recruiting_class,
        "roster": roster,
    }


async def analyze_roster(db: AsyncSession, team: str, season: int | None = None) -> str:
    roster = await get_team_roster(db, team, season)

    summary_lines = [f"Team: {team}", f"Season: {season}", "Roster by position:"]
    for pos, players in roster.items():
        names = ", ".join(f"{p['name']} ({p['year'] or '?'})" for p in players[:6])
        summary_lines.append(f"  {pos}: {names}")
    summary = "\n".join(summary_lines)

    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=(
            "You are a college football roster analyst. Analyze the team's depth chart and identify: "
            "positional strengths, depth concerns, key players graduating/entering the draft soon, "
            "and top 3 needs heading into recruiting and the transfer portal. Keep under 400 words."
        ),
        messages=[{"role": "user", "content": f"Analyze this college football roster:\n\n{summary}"}],
    )
    return response.content[0].text
