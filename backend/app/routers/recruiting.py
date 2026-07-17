from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..services.recruiting_service import list_recruits, get_team_recruits, get_recruiting_rankings, get_247_team_rankings

router = APIRouter(prefix="/recruiting", tags=["recruiting"])


@router.get("")
async def list_entries(
    class_year: Optional[int] = Query(None),
    position: Optional[str] = Query(None),
    committed_to: Optional[str] = Query(None),
    min_stars: Optional[int] = Query(None),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await list_recruits(db, class_year, position, committed_to, min_stars, limit)


@router.get("/rankings")
async def recruiting_rankings(
    class_year: Optional[int] = Query(None),
    conference: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_recruiting_rankings(db, class_year, conference)


@router.get("/team/{school}")
async def team_recruits(school: str, class_year: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    return await get_team_recruits(db, school, class_year)


@router.get("/rankings/247")
async def team_rankings_247(
    class_year: Optional[int] = Query(None),
    conference: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Real 247Sports team rankings — manual snapshot, see recruiting_service.save_247_team_rankings."""
    return await get_247_team_rankings(db, class_year, conference)
