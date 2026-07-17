from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..services.matchup_service import list_weeks, get_games_for_week, predict_game

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/weeks")
async def weeks(season: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    return await list_weeks(db, season)


@router.get("")
async def games_for_week(
    week: int = Query(...),
    season: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_games_for_week(db, week, season)


@router.post("/{game_id}/predict")
async def predict(game_id: int, force: bool = Query(False), db: AsyncSession = Depends(get_db)):
    result = await predict_game(db, game_id, force=force)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found or teams unavailable")
    return result
