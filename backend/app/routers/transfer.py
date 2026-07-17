from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..services.transfer_service import (
    list_portal_entries, get_team_portal_activity, get_portal_rankings, grade_portal_entry, _entry_dict,
)

router = APIRouter(prefix="/transfer-portal", tags=["transfer-portal"])


@router.get("")
async def list_entries(
    season: Optional[int] = Query(None),
    position: Optional[str] = Query(None),
    from_school: Optional[str] = Query(None),
    to_school: Optional[str] = Query(None),
    committed: Optional[bool] = Query(None),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await list_portal_entries(db, season, position, from_school, to_school, committed, limit)


@router.get("/rankings")
async def portal_rankings(
    season: Optional[int] = Query(None),
    conference: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_portal_rankings(db, season, conference)


@router.get("/team/{school}")
async def team_portal_activity(school: str, season: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    return await get_team_portal_activity(db, school, season)


@router.post("/{entry_id}/grade")
async def grade_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    entry = await grade_portal_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _entry_dict(entry)
