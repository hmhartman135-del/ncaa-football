from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional
from ..models.player import Player, PlayerSeasonStats

METRIC_COLUMNS = [
    "passing_yards", "passing_tds", "interceptions",
    "rushing_yards", "rushing_tds", "carries",
    "receiving_yards", "receiving_tds", "receptions",
    "tackles", "sacks", "tackles_for_loss", "interceptions_def", "passes_defended",
    "ppa_avg", "ppa_total",
]

POSITION_GROUPS = {
    "QB": ["QB"],
    "RB": ["RB", "FB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "DEF": ["DE", "DT", "LB", "CB", "S", "DB", "MLB", "OLB", "ILB", "EDGE"],
    "OL": ["OT", "OG", "C", "G", "T"],
}


async def get_leaderboard(
    db: AsyncSession,
    metric: str = "passing_yards",
    position: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 50,
):
    if season is None:
        season = (await db.execute(select(func.max(PlayerSeasonStats.season)))).scalar()
        if season is None:
            return []

    col_name = metric if metric in METRIC_COLUMNS else "passing_yards"
    stat_col = getattr(PlayerSeasonStats, col_name)

    query = (
        select(Player, PlayerSeasonStats)
        .join(PlayerSeasonStats, Player.id == PlayerSeasonStats.player_id)
        .where(PlayerSeasonStats.season == season)
        .where(stat_col.isnot(None))
    )
    if position and position in POSITION_GROUPS:
        query = query.where(Player.position.in_(POSITION_GROUPS[position]))
    elif position:
        query = query.where(Player.position == position)

    query = query.order_by(desc(stat_col)).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    leaders = []
    for rank, (player, stats) in enumerate(rows, 1):
        leaders.append({
            "rank": rank,
            "player_id": player.id,
            "name": player.name,
            "position": player.position,
            "team": player.team,
            "value": getattr(stats, col_name, None),
            "games": stats.games,
            "season": season,
        })
    return leaders
