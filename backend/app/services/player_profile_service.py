import asyncio
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.player import Player, PlayerSeasonStats
from ..models.transfer import TransferPortalEntry
from ..models.recruit import Recruit
from ..config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _stats_dict(stats: PlayerSeasonStats | None) -> dict:
    if not stats:
        return {}
    return {
        "games": stats.games,
        "completions": stats.completions, "attempts": stats.attempts,
        "passing_yards": stats.passing_yards, "passing_tds": stats.passing_tds, "interceptions": stats.interceptions,
        "carries": stats.carries, "rushing_yards": stats.rushing_yards, "rushing_tds": stats.rushing_tds,
        "targets": stats.targets, "receptions": stats.receptions,
        "receiving_yards": stats.receiving_yards, "receiving_tds": stats.receiving_tds,
        "tackles": stats.tackles, "sacks": stats.sacks, "tackles_for_loss": stats.tackles_for_loss,
        "interceptions_def": stats.interceptions_def, "passes_defended": stats.passes_defended,
        "ppa_avg": stats.ppa_avg, "ppa_total": stats.ppa_total,
    }


async def _career_rows(db: AsyncSession, anchor: Player):
    """All season/team rows for this person — matched by CFBD athlete id when we
    have one (reliable across teams/seasons), else by exact name."""
    if anchor.cfbd_id:
        where_clause = Player.cfbd_id == anchor.cfbd_id
    else:
        where_clause = Player.name == anchor.name
    result = await db.execute(
        select(Player, PlayerSeasonStats)
        .outerjoin(
            PlayerSeasonStats,
            (Player.id == PlayerSeasonStats.player_id) & (PlayerSeasonStats.season == Player.season),
        )
        .where(where_clause)
        .order_by(Player.season)
    )
    return result.all()


async def _transfer_history(db: AsyncSession, anchor: Player) -> list[TransferPortalEntry]:
    result = await db.execute(
        select(TransferPortalEntry)
        .where((TransferPortalEntry.player_id == anchor.id) | (TransferPortalEntry.player_name == anchor.name))
        .order_by(TransferPortalEntry.season)
    )
    return result.scalars().all()


async def _recruiting_profile(db: AsyncSession, anchor: Player) -> dict | None:
    """Best-effort match to this player's original HS recruiting profile, by name."""
    result = await db.execute(
        select(Recruit).where(Recruit.name == anchor.name).order_by(Recruit.class_year.desc()).limit(1)
    )
    r = result.scalar_one_or_none()
    if not r:
        return None
    return {
        "class_year": r.class_year, "stars": r.stars, "rating": r.rating,
        "national_rank": r.national_rank, "position_rank": r.position_rank,
    }


def _build_profile_dict(anchor: Player, team_history, season_stats, transfer_list, recruiting) -> dict:
    return {
        "id": anchor.id,
        "name": anchor.name,
        "position": anchor.position,
        "team": anchor.team,
        "year": anchor.year,
        "jersey": anchor.jersey,
        "height": anchor.height,
        "weight": anchor.weight,
        "home_city": anchor.home_city,
        "home_state": anchor.home_state,
        "team_history": team_history,
        "season_stats": season_stats,
        "transfers": transfer_list,
        "recruiting": recruiting,
    }


def _context_text(profile: dict) -> str:
    lines = [
        f"Name: {profile['name']}",
        f"Current/most recent team: {profile['team']}",
        f"Position: {profile['position']}",
        f"Hometown: {profile['home_city'] or ''}, {profile['home_state'] or ''}".strip(", "),
    ]
    if profile.get("recruiting"):
        rc = profile["recruiting"]
        lines.append(
            f"HS recruiting: {rc['class_year']} class, {rc['stars'] or '?'}-star "
            f"(national rank {rc['national_rank'] or 'n/a'}, position rank {rc['position_rank'] or 'n/a'})"
        )
    lines.append("")
    lines.append("Team history:")
    for th in profile["team_history"]:
        lines.append(f"  {th['season']}: {th['team']} ({th['position']}, class year {th['year'] or '?'})")

    if profile["transfers"]:
        lines.append("")
        lines.append("Transfer portal activity:")
        for t in profile["transfers"]:
            dest = t["to_school"] or "uncommitted"
            lines.append(f"  {t['season']} cycle: {t['from_school']} -> {dest} ({t['stars'] or '?'}-star, rating {t['rating'] or 'n/a'})")

    if profile["season_stats"]:
        lines.append("")
        lines.append("Season-by-season stats:")
        for s in profile["season_stats"]:
            bits = ", ".join(f"{k}={v}" for k, v in s.items() if k not in ("season", "team") and v not in (None, 0))
            lines.append(f"  {s['season']} ({s['team']}): {bits or 'no notable recorded stats'}")

    return "\n".join(lines)


async def _generate_bio(context: str) -> str:
    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=700,
        system=(
            "You are a college football analyst writing a concise, fan-facing player profile. "
            "Summarize their career path (teams played for, any transfers and why that likely happened "
            "based on timing/star rating changes), production trend across seasons, and what to expect "
            "this season. Conversational and informative, under 300 words. If data is sparse (e.g. an "
            "incoming freshman or transfer with no stats in our system yet), say so plainly and lean on "
            "recruiting profile/transfer context instead of guessing at stats."
        ),
        messages=[{"role": "user", "content": f"Write a player profile for:\n\n{context}"}],
    )
    return response.content[0].text


async def get_player_context(db: AsyncSession, player_id: int) -> dict | None:
    """Full career profile (team history, season stats, transfers, recruiting
    background) with no AI call — reusable by anything that needs real player
    data (scouting comparisons, the player detail page, etc)."""
    from .roster_service import _current_team_overrides, _drafted_players  # local import: avoids a cycle at module load time

    result = await db.execute(select(Player).where(Player.id == player_id))
    anchor = result.scalar_one_or_none()
    if not anchor:
        return None

    career_rows = await _career_rows(db, anchor)
    transfers = await _transfer_history(db, anchor)
    recruiting = await _recruiting_profile(db, anchor)

    team_history = [
        {"season": p.season, "team": p.team, "position": p.position, "year": p.year}
        for p, _ in career_rows
    ]
    season_stats = [
        {"season": p.season, "team": p.team, **_stats_dict(s)}
        for p, s in career_rows if s is not None
    ]
    transfer_list = [
        {
            "season": t.season, "from_school": t.from_school, "to_school": t.to_school,
            "stars": t.stars, "rating": t.rating, "committed": t.committed,
        }
        for t in transfers
    ]

    profile = _build_profile_dict(anchor, team_history, season_stats, transfer_list, recruiting)

    # Override with real current status — anchor.team is a frozen roster-season
    # snapshot and goes stale the moment someone transfers or gets drafted.
    drafted_ids, drafted_names = await _drafted_players(db)
    is_drafted = (anchor.cfbd_id and anchor.cfbd_id in drafted_ids) or anchor.name in drafted_names
    if is_drafted:
        profile["former_team"] = anchor.team
        profile["team"] = "NFL"
        profile["drafted"] = True
    else:
        overrides = await _current_team_overrides(db)
        current_team = overrides.get(anchor.name)
        if current_team and current_team != anchor.team:
            profile["former_team"] = anchor.team
            profile["team"] = current_team
            profile["transferred"] = True

    return profile


async def get_player_profile(db: AsyncSession, player_id: int) -> dict | None:
    profile = await get_player_context(db, player_id)
    if not profile:
        return None
    profile["ai_bio"] = await _generate_bio(_context_text(profile))
    return profile


async def get_transfer_profile(db: AsyncSession, transfer_row_id: int) -> dict | None:
    """Profile for an incoming-transfer roster entry (no Player row of its own yet).
    Falls back to the linked historical Player record's full career if we have one."""
    result = await db.execute(select(TransferPortalEntry).where(TransferPortalEntry.id == transfer_row_id))
    t = result.scalar_one_or_none()
    if not t:
        return None
    if t.player_id:
        linked = await get_player_profile(db, t.player_id)
        if linked:
            linked["team"] = t.to_school or linked["team"]
            return linked

    context = (
        f"Name: {t.player_name}\nPosition: {t.position or 'unknown'}\n"
        f"Transferring: {t.from_school or 'unknown'} -> {t.to_school or 'uncommitted'}\n"
        f"Star rating: {t.stars or 'unrated'}, Rating: {t.rating or 'n/a'}\n"
        f"Note: no prior season stats found in our system for this player.\n"
    )
    return {
        "id": f"transfer-{t.id}",
        "name": t.player_name,
        "position": t.position,
        "team": t.to_school,
        "year": t.year_in_school,
        "jersey": None, "height": None, "weight": None,
        "home_city": None, "home_state": None,
        "team_history": [],
        "season_stats": [],
        "transfers": [{
            "season": t.season, "from_school": t.from_school, "to_school": t.to_school,
            "stars": t.stars, "rating": t.rating, "committed": t.committed,
        }],
        "ai_bio": await _generate_bio(context),
    }


async def get_signee_profile(db: AsyncSession, recruit_id: int) -> dict | None:
    """Profile for an incoming high-school signee (no Player row until they enroll)."""
    result = await db.execute(select(Recruit).where(Recruit.id == recruit_id))
    r = result.scalar_one_or_none()
    if not r:
        return None

    context = (
        f"Name: {r.name}\nPosition: {r.position or 'unknown'}\n"
        f"Signing class: {r.class_year}\nCommitted to: {r.committed_to or 'uncommitted'}\n"
        f"Star rating: {r.stars or 'unrated'}, Rating: {r.rating or 'n/a'}\n"
        f"National rank: {r.national_rank or 'n/a'}, Position rank: {r.position_rank or 'n/a'}, "
        f"State rank: {r.state_rank or 'n/a'}\n"
        f"Hometown: {r.city or ''}, {r.state_province or ''}\n"
        f"Note: incoming high school signee — no college stats yet.\n"
    )
    return {
        "id": f"signee-{r.id}",
        "name": r.name,
        "position": r.position,
        "team": r.committed_to,
        "year": "HS",
        "jersey": None, "height": r.height, "weight": r.weight,
        "home_city": r.city, "home_state": r.state_province,
        "team_history": [],
        "season_stats": [],
        "transfers": [],
        "ai_bio": await _generate_bio(context),
    }
