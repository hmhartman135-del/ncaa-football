from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.roster_service import get_team_roster, get_current_roster, analyze_roster

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get("/{team}")
async def roster(team: str, season: int | None = Query(None), db: AsyncSession = Depends(get_db)):
    return await get_team_roster(db, team, season)


@router.get("/{team}/current")
async def current_roster(team: str, db: AsyncSession = Depends(get_db)):
    """Last known roster adjusted for this cycle's real portal moves + signees."""
    return await get_current_roster(db, team)


@router.get("/{team}/analyze")
async def roster_analysis(team: str, season: int | None = Query(None), db: AsyncSession = Depends(get_db)):
    analysis = await analyze_roster(db, team, season)
    return {"team": team, "season": season, "analysis": analysis}
