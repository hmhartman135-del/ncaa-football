import asyncio
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.team import Team
from ..models.player import Player, PlayerSeasonStats
from .cfbd_client import cfbd
from .roster_service import _excluded_from_roster, EXHAUSTED_ELIGIBILITY_YEARS
from ..config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# key -> (label, path into the /stats/season/advanced side dict, "high"|"low" = which direction is better)
TEAM_METRICS: dict[str, dict] = {
    "offense_ppa":                    {"label": "Offensive PPA/play",        "side": "offense", "path": ("ppa",),                          "better": "high"},
    "offense_success_rate":           {"label": "Offensive Success Rate",    "side": "offense", "path": ("successRate",),                   "better": "high"},
    "offense_explosiveness":          {"label": "Offensive Explosiveness",   "side": "offense", "path": ("explosiveness",),                 "better": "high"},
    "offense_points_per_opportunity": {"label": "Offensive Pts/Opportunity", "side": "offense", "path": ("pointsPerOpportunity",),           "better": "high"},
    "offense_line_yards":             {"label": "Offensive Line Yards/Rush", "side": "offense", "path": ("lineYards",),                      "better": "high"},
    "offense_havoc_allowed":          {"label": "Offensive Havoc Allowed",   "side": "offense", "path": ("havoc", "total"),                  "better": "low"},
    "defense_ppa":                    {"label": "Defensive PPA/play Allowed","side": "defense", "path": ("ppa",),                          "better": "low"},
    "defense_success_rate":           {"label": "Defensive Success Rate Allowed", "side": "defense", "path": ("successRate",),              "better": "low"},
    "defense_explosiveness":          {"label": "Defensive Explosiveness Allowed", "side": "defense", "path": ("explosiveness",),           "better": "low"},
    "defense_points_per_opportunity": {"label": "Defensive Pts/Opportunity Allowed", "side": "defense", "path": ("pointsPerOpportunity",), "better": "low"},
    "defense_line_yards":             {"label": "Defensive Line Yards/Rush Allowed", "side": "defense", "path": ("lineYards",),            "better": "low"},
    "defense_havoc":                  {"label": "Defensive Havoc Rate",      "side": "defense", "path": ("havoc", "total"),                  "better": "high"},
}


def _dig(d: dict, path: tuple) -> float | None:
    for key in path:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


async def _resolve_stats_season(year: int) -> tuple[int, list[dict]]:
    """CFBD's advanced-stats endpoints are computed from actual games — empty
    until the season is underway. Falls back to the prior season if so."""
    data = await cfbd.team_advanced_stats(year)
    if data:
        return year, data
    data = await cfbd.team_advanced_stats(year - 1)
    return year - 1, data


async def get_team_full_stats(db: AsyncSession, school: str, season: int | None = None) -> dict | None:
    team_season = season or (await db.execute(select(func.max(Team.season)))).scalar()
    if team_season is None:
        return None

    resolved_season, all_advanced = await _resolve_stats_season(team_season)
    advanced = next((t for t in all_advanced if t.get("team") == school), None)

    season_totals_raw = await cfbd.team_season_stats(resolved_season, team=school)
    season_totals = {row["statName"]: row["statValue"] for row in season_totals_raw}

    usage_raw = await cfbd.player_usage(resolved_season, team=school)
    usage_by_name = {u["name"]: u.get("usage", {}) for u in usage_raw}

    roster_season = (await db.execute(
        select(func.max(Player.season)).where(Player.team == school)
    )).scalar()
    players = []
    if roster_season is not None:
        departed_names, drafted_ids, drafted_names = await _excluded_from_roster(db, school)
        result = await db.execute(
            select(Player, PlayerSeasonStats)
            .outerjoin(
                PlayerSeasonStats,
                (Player.id == PlayerSeasonStats.player_id) & (PlayerSeasonStats.season == roster_season),
            )
            .where(Player.team == school, Player.season == roster_season)
        )
        for player, stats in result.all():
            if player.name in departed_names or player.year in EXHAUSTED_ELIGIBILITY_YEARS:
                continue
            if (player.cfbd_id and player.cfbd_id in drafted_ids) or player.name in drafted_names:
                continue
            players.append({
                "id": player.id,
                "name": player.name,
                "position": player.position,
                "usage": usage_by_name.get(player.name),
                "stats": {
                    "games": stats.games, "passing_yards": stats.passing_yards, "passing_tds": stats.passing_tds,
                    "rushing_yards": stats.rushing_yards, "rushing_tds": stats.rushing_tds,
                    "receptions": stats.receptions, "receiving_yards": stats.receiving_yards, "receiving_tds": stats.receiving_tds,
                    "tackles": stats.tackles, "sacks": stats.sacks, "tackles_for_loss": stats.tackles_for_loss,
                    "interceptions_def": stats.interceptions_def, "passes_defended": stats.passes_defended,
                    "ppa_avg": stats.ppa_avg, "ppa_total": stats.ppa_total,
                } if stats else None,
            })
        players.sort(key=lambda p: (p["usage"] or {}).get("overall", 0) or 0, reverse=True)

    return {
        "school": school,
        "stats_season": resolved_season,
        "roster_season": roster_season,
        "advanced": advanced,
        "season_totals": season_totals,
        "players": players,
    }


async def get_team_stat_rankings(db: AsyncSession, metric: str, season: int | None = None, conference: str | None = None) -> dict:
    if metric not in TEAM_METRICS:
        metric = "offense_ppa"
    spec = TEAM_METRICS[metric]

    team_season = season or (await db.execute(select(func.max(Team.season)))).scalar()
    if team_season is None:
        return {"metric": metric, "label": spec["label"], "better": spec["better"], "season": None, "rankings": []}

    resolved_season, all_advanced = await _resolve_stats_season(team_season)

    conference_by_school = {}
    if conference:
        rows = (await db.execute(
            select(Team.school, Team.conference).where(Team.season == team_season, Team.conference == conference)
        )).all()
        conference_by_school = {school: conf for school, conf in rows}

    rankings = []
    for row in all_advanced:
        school = row.get("team")
        if conference and school not in conference_by_school:
            continue
        value = _dig(row.get(spec["side"], {}), spec["path"])
        if value is None:
            continue
        rankings.append({"school": school, "conference": row.get("conference"), "value": round(value, 4)})

    rankings.sort(key=lambda r: r["value"], reverse=(spec["better"] == "high"))
    for i, r in enumerate(rankings, start=1):
        r["rank"] = i

    return {"metric": metric, "label": spec["label"], "better": spec["better"], "season": resolved_season, "rankings": rankings}


def _fmt(v, decimals=3):
    return f"{v:.{decimals}f}" if isinstance(v, (int, float)) else "n/a"


def _stats_context_text(data: dict) -> str:
    adv = data["advanced"] or {}
    off, defn = adv.get("offense") or {}, adv.get("defense") or {}
    lines = [
        f"Team: {data['school']} — {data['stats_season']} season advanced stats",
        "",
        f"Offense: PPA/play {_fmt(off.get('ppa'))}, success rate {_fmt(off.get('successRate'))}, "
        f"explosiveness {_fmt(off.get('explosiveness'))}, pts/opportunity {_fmt(off.get('pointsPerOpportunity'), 2)}, "
        f"line yards/rush {_fmt(off.get('lineYards'), 2)}, havoc allowed {_fmt((off.get('havoc') or {}).get('total'))}",
        f"Defense: PPA/play allowed {_fmt(defn.get('ppa'))}, success rate allowed {_fmt(defn.get('successRate'))}, "
        f"explosiveness allowed {_fmt(defn.get('explosiveness'))}, pts/opportunity allowed {_fmt(defn.get('pointsPerOpportunity'), 2)}, "
        f"line yards/rush allowed {_fmt(defn.get('lineYards'), 2)}, havoc rate {_fmt((defn.get('havoc') or {}).get('total'))}",
    ]
    top_usage = sorted(
        (p for p in data["players"] if p.get("usage")),
        key=lambda p: p["usage"].get("overall", 0), reverse=True,
    )[:8]
    if top_usage:
        lines.append("")
        lines.append("Top players by offensive usage share:")
        for p in top_usage:
            u = p["usage"]
            ppa = (p.get("stats") or {}).get("ppa_total")
            lines.append(f"  {p['name']} ({p['position']}): {u.get('overall', 0)*100:.0f}% overall usage" + (f", PPA total {ppa}" if ppa is not None else ""))
    return "\n".join(lines)


async def generate_team_stats_analysis(db: AsyncSession, school: str, season: int | None = None) -> dict | None:
    """AI breakdown of a team's advanced stats profile — schematic identity,
    strengths/weaknesses, statistical outliers. Distinct from team_service's
    'Discuss This Team' (roster/schedule/offseason narrative) — this one is
    purely about what the advanced numbers say."""
    data = await get_team_full_stats(db, school, season)
    if not data:
        return None
    if not data.get("advanced"):
        data["ai_analysis"] = (
            f"No {season or data['stats_season']} season advanced stats available yet to analyze"
            + (" — the season hasn't started." if season and season > data["stats_season"] else ".")
        )
        return data

    context = _stats_context_text(data)
    response = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=900,
        system=(
            "You are a college football analytics expert. Given a team's advanced stats profile "
            "(PPA, success rate, explosiveness, havoc, line yards, and top players by usage), write "
            "an analytical breakdown covering: their offensive and defensive statistical identity "
            "(e.g. explosive vs. efficient offense, aggressive vs. bend-don't-break defense), the "
            "biggest strength and biggest weakness the numbers reveal, any stat that stands out as "
            "unusual, and how their key players' usage rates reflect their scheme. Be specific and "
            "cite the actual numbers. Under 400 words."
        ),
        messages=[{"role": "user", "content": f"Analyze this team's advanced stats profile:\n\n{context}"}],
    )
    data["ai_analysis"] = response.content[0].text
    return data
