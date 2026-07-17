import asyncio
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from ..models.team import Team
from ..models.player import Player, PlayerSeasonStats
from ..models.transfer import TransferPortalEntry
from ..models.recruit import Recruit
from ..models.game import Game
from ..services.cfbd_client import cfbd
from ..services.roster_service import _drafted_players
from ..config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

EXHAUSTED_ELIGIBILITY_YEARS = {"4"}  # mirrors roster_service — 4th-year players in the base season are assumed graduated


async def _resolve_season(db: AsyncSession, school: str) -> int | None:
    result = await db.execute(select(func.max(Team.season)).where(Team.school == school))
    return result.scalar()


def _stat_bits(s: PlayerSeasonStats) -> str:
    bits = []
    for label, val in [
        ("pass yds", s.passing_yards), ("pass TD", s.passing_tds),
        ("rush yds", s.rushing_yards), ("rush TD", s.rushing_tds),
        ("rec", s.receptions), ("rec yds", s.receiving_yards), ("rec TD", s.receiving_tds),
        ("tackles", s.tackles), ("sacks", s.sacks), ("TFL", s.tackles_for_loss),
    ]:
        if val:
            bits.append(f"{val} {label}")
    return ", ".join(bits)


async def _best_returning_players(db: AsyncSession, school: str, roster_season: int, portal_cycle: int | None, limit: int = 8):
    departed_names: set[str] = set()
    if portal_cycle is not None:
        result = await db.execute(
            select(TransferPortalEntry.player_name)
            .where(TransferPortalEntry.season == portal_cycle, TransferPortalEntry.from_school == school)
        )
        departed_names = {name for (name,) in result.all()}

    result = await db.execute(
        select(Player, PlayerSeasonStats)
        .join(PlayerSeasonStats, Player.id == PlayerSeasonStats.player_id)
        .where(Player.team == school, Player.season == roster_season, PlayerSeasonStats.ppa_total.isnot(None))
        .order_by(PlayerSeasonStats.ppa_total.desc())
    )
    drafted_ids, drafted_names = await _drafted_players(db)

    players = []
    for player, stats in result.all():
        if player.name in departed_names or player.year in EXHAUSTED_ELIGIBILITY_YEARS:
            continue
        if (player.cfbd_id and player.cfbd_id in drafted_ids) or player.name in drafted_names:
            continue
        players.append({
            "name": player.name, "position": player.position, "year": player.year,
            "ppa_total": round(stats.ppa_total, 1) if stats.ppa_total else None,
            "stat_line": _stat_bits(stats),
        })
        if len(players) >= limit:
            break
    return players


async def get_team_analysis(db: AsyncSession, school: str) -> dict | None:
    season = await _resolve_season(db, school)
    if season is None:
        return None

    result = await db.execute(select(Team).where(Team.school == school, Team.season == season))
    current_team = result.scalar_one_or_none()
    if not current_team:
        return None

    result = await db.execute(select(Team).where(Team.school == school, Team.season == season - 1))
    last_season_team = result.scalar_one_or_none()

    portal_cycle = (await db.execute(select(func.max(TransferPortalEntry.season)))).scalar()
    departed, incoming_transfers = [], []
    if portal_cycle is not None:
        result = await db.execute(
            select(TransferPortalEntry)
            .where(TransferPortalEntry.season == portal_cycle, TransferPortalEntry.from_school == school)
        )
        departed = result.scalars().all()
        result = await db.execute(
            select(TransferPortalEntry).where(
                TransferPortalEntry.season == portal_cycle,
                TransferPortalEntry.to_school == school,
                TransferPortalEntry.committed.is_(True),
            )
        )
        incoming_transfers = result.scalars().all()

    recruiting_class = (await db.execute(select(func.max(Recruit.class_year)))).scalar()
    signees = []
    if recruiting_class is not None:
        result = await db.execute(
            select(Recruit).where(
                Recruit.class_year == recruiting_class,
                Recruit.committed_to == school,
                Recruit.committed.is_(True),
            )
        )
        signees = result.scalars().all()

    result = await db.execute(
        select(Game)
        .where(Game.season == season, or_(Game.home_team == school, Game.away_team == school))
        .order_by(Game.week)
    )
    games = result.scalars().all()

    schedule = []
    completed_games = []
    for g in games:
        is_home = g.home_team == school
        opponent = g.away_team if is_home else g.home_team
        team_pts = g.home_points if is_home else g.away_points
        opp_pts = g.away_points if is_home else g.home_points
        entry = {
            "week": g.week,
            "opponent": opponent,
            "location": "home" if is_home and not g.neutral_site else ("neutral" if g.neutral_site else "away"),
            "date": g.start_date.isoformat() if g.start_date else None,
            "completed": g.completed,
            "team_points": team_pts,
            "opponent_points": opp_pts,
        }
        schedule.append(entry)
        if g.completed:
            completed_games.append(entry)

    record_so_far = None
    if completed_games:
        w = sum(1 for g in completed_games if (g["team_points"] or 0) > (g["opponent_points"] or 0))
        l = len(completed_games) - w
        record_so_far = {"wins": w, "losses": l, "games": completed_games}

    best_players = await _best_returning_players(db, school, season - 1, portal_cycle)

    sp = None
    try:
        sp_ratings = await cfbd.sp_ratings(season)
        if not sp_ratings:
            sp_ratings = await cfbd.sp_ratings(season - 1)  # SP+ isn't computed until the season is underway
        sp = next((r for r in sp_ratings if r.get("team") == school), None)
    except Exception:
        pass

    return {
        "team": {
            "school": current_team.school, "mascot": current_team.mascot, "conference": current_team.conference,
            "logo": current_team.logo, "color": current_team.color,
            "ap_rank": current_team.ap_rank, "sp_rating": sp,
        },
        "last_season": {
            "season": season - 1,
            "wins": last_season_team.wins if last_season_team else None,
            "losses": last_season_team.losses if last_season_team else None,
            "conference_wins": last_season_team.conference_wins if last_season_team else None,
            "conference_losses": last_season_team.conference_losses if last_season_team else None,
        } if last_season_team else None,
        "best_players": best_players,
        "offseason": {
            "portal_cycle": portal_cycle,
            "departed": [{"name": d.player_name, "position": d.position, "to_school": d.to_school, "stars": d.stars} for d in departed],
            "incoming_transfers": [{"name": t.player_name, "position": t.position, "from_school": t.from_school, "stars": t.stars} for t in incoming_transfers],
            "recruiting_class": recruiting_class,
            "signees": [{"name": r.name, "position": r.position, "stars": r.stars, "national_rank": r.national_rank} for r in signees],
        },
        "season": season,
        "schedule": schedule,
        "record_so_far": record_so_far,
    }


def _context_text(analysis: dict) -> str:
    t = analysis["team"]
    lines = [
        f"Team: {t['school']} ({t['mascot']}) — {t['conference']}",
        f"Current AP rank: {t['ap_rank'] or 'unranked'}",
    ]
    if t.get("sp_rating"):
        sp = t["sp_rating"]
        lines.append(f"SP+ rating: {sp.get('rating', 'n/a')} (offense {sp.get('offense', {}).get('rating', 'n/a')}, defense {sp.get('defense', {}).get('rating', 'n/a')})")

    ls = analysis["last_season"]
    if ls:
        lines.append(f"\n{ls['season']} season record: {ls['wins']}-{ls['losses']} ({ls['conference_wins']}-{ls['conference_losses']} conference)")

    if analysis["best_players"]:
        lines.append(f"\nTop returning players (by production, {ls['season'] if ls else ''} stats):")
        for p in analysis["best_players"]:
            lines.append(f"  {p['name']} ({p['position']}, class {p['year']}) — {p['stat_line'] or 'limited stats'}, PPA total {p['ppa_total']}")

    off = analysis["offseason"]
    lines.append(f"\nOffseason activity ({off['portal_cycle']} portal cycle / {off['recruiting_class']} signing class):")
    lines.append(f"  Departed via portal: {len(off['departed'])} players" + (
        " — " + ", ".join(f"{d['name']} ({d['position']}) to {d['to_school'] or 'uncommitted'}" for d in off['departed'][:8]) if off['departed'] else ""
    ))
    lines.append(f"  Incoming transfers: {len(off['incoming_transfers'])} players" + (
        " — " + ", ".join(f"{d['name']} ({d['position']}) from {d['from_school']}" for d in off['incoming_transfers'][:8]) if off['incoming_transfers'] else ""
    ))
    lines.append(f"  Signed recruits: {len(off['signees'])} players" + (
        " — " + ", ".join(f"{d['name']} ({d['position']}, {d['stars']}★)" for d in sorted(off['signees'], key=lambda x: -(x['stars'] or 0))[:8]) if off['signees'] else ""
    ))

    lines.append(f"\n{analysis['season']} schedule ({len(analysis['schedule'])} games):")
    for g in analysis["schedule"][:16]:
        loc = {"home": "vs", "away": "@", "neutral": "vs (neutral)"}[g["location"]]
        if g["completed"]:
            result = "W" if (g["team_points"] or 0) > (g["opponent_points"] or 0) else "L"
            lines.append(f"  Week {g['week']}: {loc} {g['opponent']} — {result} {g['team_points']}-{g['opponent_points']}")
        else:
            lines.append(f"  Week {g['week']}: {loc} {g['opponent']} — not yet played")

    if analysis["record_so_far"]:
        rs = analysis["record_so_far"]
        lines.append(f"\nCurrent in-season record: {rs['wins']}-{rs['losses']}")
    else:
        lines.append("\nSeason has not started yet — this is a preseason/offseason outlook.")

    return "\n".join(lines)


async def generate_team_discussion(db: AsyncSession, school: str) -> dict | None:
    analysis = await get_team_analysis(db, school)
    if not analysis:
        return None

    context = _context_text(analysis)
    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=1400,
        system=(
            "You are a college football analyst giving a fan a comprehensive rundown of their team. "
            "Cover, in this order: (1) how they did last season, (2) their offseason — key departures, "
            "transfer portal additions, and notable signees, (3) their best/most important returning players, "
            "(4) what to look forward to and a realistic projection for this season, and (5) if the season is "
            "already underway based on the schedule provided, how they're actually doing so far (record, recent "
            "results) — otherwise note it's still preseason. Be specific, cite real names/stats given, and give "
            "an honest, opinionated take, not just a recap. Under 600 words."
        ),
        messages=[{"role": "user", "content": f"Give me the full rundown on this team:\n\n{context}"}],
    )
    analysis["ai_discussion"] = response.content[0].text
    return analysis
