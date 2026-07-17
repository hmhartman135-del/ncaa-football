from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..services.recruiting_service import (
    list_recruits, get_team_recruits, get_recruiting_rankings, get_247_team_rankings,
    save_247_recruits, save_247_team_rankings,
)

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


@router.post("/admin/load-247-players")
async def load_247_players(
    class_year: int = Query(...),
    rows: list[dict] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Load/replace a manual 247Sports player-rankings snapshot for a class year.
    Body is a JSON list of recruit dicts (name/position/stars/rating/
    national_rank/position_rank/state_rank/city/state_province/committed_to/
    committed), as pulled off a 247Sports.com recruit-rankings page."""
    count = await save_247_recruits(db, class_year, rows)
    return {"class_year": class_year, "loaded": count}


@router.post("/admin/load-247-team-rankings")
async def load_247_team_rankings(
    class_year: int = Query(...),
    rows: list[dict] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Load/replace a manual 247Sports team-rankings snapshot for a class year.
    Body is a JSON list of dicts (rank/school/commits/avg_rating/points)."""
    count = await save_247_team_rankings(db, class_year, rows)
    return {"class_year": class_year, "loaded": count}
