from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..services.rankings_service import list_ranking_weeks, get_ap_poll, get_cached_ai_top25, generate_ai_top25

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/weeks")
async def weeks(season: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    return await list_ranking_weeks(db, season)


@router.get("/poll")
async def poll(season: Optional[int] = Query(None), week: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    return await get_ap_poll(db, season, week)


@router.get("/ai-top25")
async def ai_top25_cached(season: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    result = await get_cached_ai_top25(db, season)
    return result or {"season": season, "generated_at": None, "rankings": []}


@router.post("/ai-top25")
async def ai_top25_generate(season: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    result = await generate_ai_top25(db, season)
    if not result:
        raise HTTPException(status_code=404, detail="No team data available to rank")
    return result
