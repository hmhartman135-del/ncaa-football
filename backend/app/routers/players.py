from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from ..database import get_db
from ..models.player import Player, PlayerSeasonStats
from ..services.player_profile_service import get_player_profile, get_transfer_profile, get_signee_profile
from ..services.roster_service import _current_team_overrides, _drafted_players

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/profile/{ref}")
async def player_profile(ref: str, db: AsyncSession = Depends(get_db)):
    """AI-written career profile. `ref` is a Player id for a real roster player,
    or a synthetic `transfer-{id}` / `signee-{id}` ref from the current-roster view."""
    if ref.startswith("transfer-"):
        profile = await get_transfer_profile(db, int(ref.removeprefix("transfer-")))
    elif ref.startswith("signee-"):
        profile = await get_signee_profile(db, int(ref.removeprefix("signee-")))
    else:
        profile = await get_player_profile(db, int(ref))
    if not profile:
        raise HTTPException(status_code=404, detail="Player not found")
    return profile


def _player_dict(p: Player, overrides: dict[str, str] | None = None, drafted_ids: set[int] | None = None, drafted_names: set[str] | None = None) -> dict:
    overrides = overrides or {}
    drafted_ids = drafted_ids or set()
    drafted_names = drafted_names or set()
    is_drafted = (p.cfbd_id and p.cfbd_id in drafted_ids) or p.name in drafted_names
    current_team = overrides.get(p.name)
    return {
        "id": p.id,
        "name": p.name,
        "position": p.position,
        "team": ("NFL" if is_drafted else (current_team or p.team)),
        "former_team": p.team if (is_drafted or (current_team and current_team != p.team)) else None,
        "drafted": bool(is_drafted),
        "transferred": bool(current_team and current_team != p.team and not is_drafted),
        "jersey": p.jersey,
        "year": p.year,
        "height": p.height,
        "weight": p.weight,
        "home_city": p.home_city,
        "home_state": p.home_state,
        "season": p.season,
        "draft_eligible": p.draft_eligible,
    }


@router.get("")
async def list_players(
    position: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    if season is None:
        season = (await db.execute(select(func.max(Player.season)))).scalar()
        if season is None:
            return []

    query = select(Player).where(Player.season == season)
    if position:
        query = query.where(Player.position == position)
    if team:
        query = query.where(Player.team == team)
    if search:
        query = query.where(Player.name.ilike(f"%{search}%"))
    query = query.order_by(Player.name).limit(limit).offset(offset)
    result = await db.execute(query)
    players = result.scalars().all()

    overrides = await _current_team_overrides(db)
    drafted_ids, drafted_names = await _drafted_players(db)
    return [_player_dict(p, overrides, drafted_ids, drafted_names) for p in players]


@router.get("/{player_id}")
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    stats_result = await db.execute(
        select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == player_id)
    )
    stats = stats_result.scalar_one_or_none()

    overrides = await _current_team_overrides(db)
    drafted_ids, drafted_names = await _drafted_players(db)
    data = _player_dict(player, overrides, drafted_ids, drafted_names)
    if stats:
        data["stats"] = {
            "games": stats.games,
            "completions": stats.completions, "attempts": stats.attempts,
            "passing_yards": stats.passing_yards, "passing_tds": stats.passing_tds,
            "interceptions": stats.interceptions,
            "carries": stats.carries, "rushing_yards": stats.rushing_yards, "rushing_tds": stats.rushing_tds,
            "targets": stats.targets, "receptions": stats.receptions,
            "receiving_yards": stats.receiving_yards, "receiving_tds": stats.receiving_tds,
            "tackles": stats.tackles, "sacks": stats.sacks, "tackles_for_loss": stats.tackles_for_loss,
            "interceptions_def": stats.interceptions_def, "passes_defended": stats.passes_defended,
            "ppa_avg": stats.ppa_avg, "ppa_total": stats.ppa_total,
        }
    return data
