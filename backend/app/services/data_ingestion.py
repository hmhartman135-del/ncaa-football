import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.team import Team
from ..models.player import Player, PlayerSeasonStats
from ..models.recruit import Recruit
from ..models.transfer import TransferPortalEntry
from ..models.game import Game
from ..models.nfl_draft_pick import NflDraftPick
from .cfbd_client import cfbd

logger = logging.getLogger(__name__)


def _g(d: dict, *keys, default=None):
    """Get the first present key from a dict — CFBD's JSON casing varies by endpoint."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


async def ingest_teams(db: AsyncSession, year: int) -> int:
    teams = await cfbd.teams(year)
    records = {r["team"]: r for r in await cfbd.team_records(year) if r.get("team")}
    count = 0
    for t in teams:
        school = _g(t, "school")
        if not school:
            continue
        rec = records.get(school, {})
        total = rec.get("total", {}) if isinstance(rec, dict) else {}
        conf_games = rec.get("conferenceGames", {}) if isinstance(rec, dict) else {}
        logos = _g(t, "logos", default=[])
        db.add(Team(
            cfbd_id=_g(t, "id"),
            school=school,
            mascot=_g(t, "mascot"),
            conference=_g(t, "conference"),
            division=_g(t, "division"),
            classification=_g(t, "classification"),
            color=_g(t, "color"),
            alt_color=_g(t, "alternateColor", "alt_color"),
            logo=logos[0] if logos else None,
            wins=total.get("wins"),
            losses=total.get("losses"),
            conference_wins=conf_games.get("wins"),
            conference_losses=conf_games.get("losses"),
            season=year,
        ))
        count += 1
    await db.commit()
    logger.info("Ingested %d teams for %d", count, year)
    return count


async def ingest_games(db: AsyncSession, year: int) -> int:
    games = await cfbd.games(year)
    count = 0
    for g in games:
        start_raw = _g(g, "startDate")
        start_date = None
        if start_raw:
            try:
                start_date = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                pass
        db.add(Game(
            cfbd_id=_g(g, "id"),
            season=year,
            week=_g(g, "week"),
            season_type=_g(g, "seasonType"),
            start_date=start_date,
            completed=bool(_g(g, "completed", default=False)),
            neutral_site=bool(_g(g, "neutralSite", default=False)),
            venue=_g(g, "venue"),
            notes=_g(g, "notes"),
            home_team=_g(g, "homeTeam"),
            home_conference=_g(g, "homeConference"),
            home_points=_g(g, "homePoints"),
            away_team=_g(g, "awayTeam"),
            away_conference=_g(g, "awayConference"),
            away_points=_g(g, "awayPoints"),
        ))
        count += 1
    await db.commit()
    logger.info("Ingested %d games for %d", count, year)
    return count


async def ingest_draft_picks(db: AsyncSession, year: int) -> int:
    picks = await cfbd.draft_picks(year)
    count = 0
    for p in picks:
        name = _g(p, "name")
        if not name:
            continue
        db.add(NflDraftPick(
            cfbd_athlete_id=_g(p, "collegeAthleteId"),
            name=name,
            college_team=_g(p, "collegeTeam"),
            position=_g(p, "position"),
            draft_year=year,
            round=_g(p, "round"),
            pick=_g(p, "pick"),
            nfl_team=_g(p, "nflTeam"),
        ))
        count += 1
    await db.commit()
    logger.info("Ingested %d NFL draft picks for %d", count, year)
    return count


async def ingest_rosters(db: AsyncSession, year: int) -> tuple[int, int]:
    """CFBD doesn't publish a season's roster until close to kickoff — fall back to
    the most recent prior year with data so the app isn't empty in the offseason."""
    roster = await cfbd.roster(year)
    resolved_year = year
    if not roster:
        roster = await cfbd.roster(year - 1)
        resolved_year = year - 1
        if roster:
            logger.info("No roster published for %d yet — using %d instead", year, resolved_year)

    count = 0
    for p in roster:
        first = _g(p, "firstName", "first_name", default="")
        last = _g(p, "lastName", "last_name", default="")
        name = _g(p, "name", default=f"{first} {last}".strip())
        if not name:
            continue
        year_in_school = _g(p, "year", "yearIn", "class")
        db.add(Player(
            cfbd_id=_g(p, "id"),
            name=name,
            position=_g(p, "position"),
            team=_g(p, "team"),
            jersey=_g(p, "jersey"),
            year=str(year_in_school) if year_in_school is not None else None,
            height=_g(p, "height"),
            weight=_g(p, "weight"),
            home_city=_g(p, "homeCity", "home_city"),
            home_state=_g(p, "homeState", "home_state"),
            season=resolved_year,
            draft_eligible=str(year_in_school) in ("3", "4", "5", "JR", "SR", "GR"),
        ))
        count += 1
    await db.commit()
    logger.info("Ingested %d roster players for %d", count, resolved_year)
    return count, resolved_year


async def ingest_season_stats(db: AsyncSession, year: int) -> int:
    """CFBD returns one row per (player, category, statType) — pivot into per-player rows."""
    raw = await cfbd.player_season_stats(year)
    ppa = await cfbd.player_ppa_season(year)

    result = await db.execute(select(Player).where(Player.season == year))
    players_by_name = {p.name: p for p in result.scalars().all()}

    STAT_MAP = {
        ("passing", "COMPLETIONS"): "completions",
        ("passing", "ATT"): "attempts",
        ("passing", "YDS"): "passing_yards",
        ("passing", "TD"): "passing_tds",
        ("passing", "INT"): "interceptions",
        ("rushing", "CAR"): "carries",
        ("rushing", "YDS"): "rushing_yards",
        ("rushing", "TD"): "rushing_tds",
        ("receiving", "REC"): "receptions",
        ("receiving", "YDS"): "receiving_yards",
        ("receiving", "TD"): "receiving_tds",
        ("defensive", "TOT"): "tackles",
        ("defensive", "SACKS"): "sacks",
        ("defensive", "TFL"): "tackles_for_loss",
        ("interceptions", "INT"): "interceptions_def",
        ("defensive", "PD"): "passes_defended",
    }

    pivot: dict[str, dict] = {}
    for row in raw:
        player_name = _g(row, "player")
        if not player_name:
            continue
        category = _g(row, "category")
        stat_type = _g(row, "statType")
        stat_val = _g(row, "stat")
        field = STAT_MAP.get((category, stat_type))
        if not field:
            continue
        bucket = pivot.setdefault(player_name, {})
        try:
            bucket[field] = float(stat_val) if "." in str(stat_val) else int(stat_val)
        except (TypeError, ValueError):
            continue

    ppa_by_name = {_g(row, "name"): row for row in ppa if _g(row, "name")}

    count = 0
    for player_name, stats in pivot.items():
        player = players_by_name.get(player_name)
        if not player:
            continue
        ppa_row = ppa_by_name.get(player_name, {})
        avg_ppa = (ppa_row.get("averagePPA") or {}).get("all")
        total_ppa = (ppa_row.get("totalPPA") or {}).get("all")
        db.add(PlayerSeasonStats(
            player_id=player.id,
            season=year,
            ppa_avg=avg_ppa,
            ppa_total=total_ppa,
            **stats,
        ))
        count += 1
    await db.commit()
    logger.info("Ingested season stats for %d players in %d", count, year)
    return count


async def ingest_recruiting(db: AsyncSession, class_year: int) -> int:
    """CFBD's `/recruiting/players` only gives a national `ranking` — no
    position or state rank. We derive those ourselves (real, from the same
    rating CFBD gives us) rather than leaving them null or fabricating them."""
    recruits = await cfbd.recruiting_players(class_year)

    parsed = []
    for r in recruits:
        name = _g(r, "name")
        if not name:
            continue
        parsed.append({
            "cfbd_id": _g(r, "id", "athleteId"),
            "name": name,
            "position": _g(r, "position"),
            "stars": _g(r, "stars"),
            "rating": _g(r, "rating") or 0,
            "national_rank": _g(r, "ranking"),
            "height": _g(r, "height"),
            "weight": _g(r, "weight"),
            "city": _g(r, "city"),
            "state_province": _g(r, "stateProvince", "state_province"),
            "committed_to": _g(r, "committedTo", "committed_to"),
        })

    # Derive position_rank / state_rank by sorting within each group by rating desc.
    by_position: dict[str, list] = {}
    by_state: dict[str, list] = {}
    for p in parsed:
        if p["position"]:
            by_position.setdefault(p["position"], []).append(p)
        if p["state_province"]:
            by_state.setdefault(p["state_province"], []).append(p)
    for group in by_position.values():
        group.sort(key=lambda p: p["rating"], reverse=True)
        for i, p in enumerate(group, start=1):
            p["position_rank"] = i
    for group in by_state.values():
        group.sort(key=lambda p: p["rating"], reverse=True)
        for i, p in enumerate(group, start=1):
            p["state_rank"] = i

    count = 0
    for p in parsed:
        committed_to = p["committed_to"]
        db.add(Recruit(
            cfbd_id=p["cfbd_id"],
            name=p["name"],
            position=p["position"],
            class_year=class_year,
            stars=p["stars"],
            rating=p["rating"] or None,
            national_rank=p["national_rank"],
            position_rank=p.get("position_rank"),
            state_rank=p.get("state_rank"),
            height=p["height"],
            weight=p["weight"],
            city=p["city"],
            state_province=p["state_province"],
            committed_to=committed_to,
            committed=bool(committed_to),
        ))
        count += 1
    await db.commit()
    logger.info("Ingested %d recruits for class of %d", count, class_year)
    return count


CLASS_YEAR_LABELS = {"0": "Freshman", "1": "Freshman", "2": "Sophomore", "3": "Junior", "4": "Senior"}


def _classify_class_year(player_year: str | None) -> str | None:
    """Map our roster's numeric `year` field to a Fr/So/Jr/Sr label. CFBD's
    portal endpoint has no class-year field at all, so this is derived from
    the player's own roster record at the time they entered the portal —
    NOT available (and not guessed) if we have no linked roster record.
    Note: this cannot detect redshirt status — CFBD exposes no such field
    anywhere in the roster or portal data, so redshirt seasons are simply
    unknown to this app."""
    if player_year is None:
        return None
    if player_year in CLASS_YEAR_LABELS:
        return CLASS_YEAR_LABELS[player_year]
    if player_year.isdigit() and int(player_year) >= 5:
        return "5th-Year Senior"
    return None  # covers CFBD data artifacts like a raw enrollment year (e.g. "2025")


async def ingest_transfer_portal(db: AsyncSession, year: int) -> int:
    entries = await cfbd.transfer_portal(year)
    result = await db.execute(select(Player).where(Player.season == year - 1))
    players_by_name = {p.name: p for p in result.scalars().all()}

    count = 0
    for e in entries:
        first = _g(e, "firstName", default="")
        last = _g(e, "lastName", default="")
        name = _g(e, "name", default=f"{first} {last}".strip())
        if not name:
            continue
        origin = _g(e, "origin", "fromSchool")
        destination = _g(e, "destination", "toSchool")
        linked = players_by_name.get(name)

        entered_raw = _g(e, "transferDate")
        entered_date = None
        if entered_raw:
            try:
                entered_date = datetime.fromisoformat(entered_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                pass

        db.add(TransferPortalEntry(
            cfbd_id=_g(e, "id"),
            player_name=name,
            position=_g(e, "position"),
            from_school=origin,
            to_school=destination,
            season=year,
            year_in_school=_classify_class_year(linked.year if linked else None),
            eligibility_status=_g(e, "eligibility"),
            stars=_g(e, "stars"),
            rating=_g(e, "rating"),
            committed=bool(destination),
            entered_date=entered_date,
            player_id=linked.id if linked else None,
        ))
        count += 1
    await db.commit()
    logger.info("Ingested %d transfer portal entries for %d", count, year)
    return count
