from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from ..database import get_db
from ..models.team import Team
from ..services.team_service import get_team_analysis, generate_team_discussion
from ..services.matchup_service import predict_team_season

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/{school}/analysis")
async def team_analysis(school: str, db: AsyncSession = Depends(get_db)):
    analysis = await get_team_analysis(db, school)
    if not analysis:
        raise HTTPException(status_code=404, detail="Team not found")
    return analysis


@router.get("/{school}/discuss")
async def team_discussion(school: str, db: AsyncSession = Depends(get_db)):
    analysis = await generate_team_discussion(db, school)
    if not analysis:
        raise HTTPException(status_code=404, detail="Team not found")
    return analysis


@router.post("/{school}/predict-season")
async def predict_season(school: str, force: bool = Query(False), db: AsyncSession = Depends(get_db)):
    """Projects the team's full-season record: real results for games already
    played, AI predictions (generated on the fly, cached per-game) for the rest."""
    result = await predict_team_season(db, school, force=force)
    if not result:
        raise HTTPException(status_code=404, detail="Team or schedule not found")
    return result


def _team_dict(t: Team) -> dict:
    return {
        "id": t.id,
        "school": t.school,
        "mascot": t.mascot,
        "conference": t.conference,
        "division": t.division,
        "classification": t.classification,
        "color": t.color,
        "alt_color": t.alt_color,
        "logo": t.logo,
        "wins": t.wins,
        "losses": t.losses,
        "conference_wins": t.conference_wins,
        "conference_losses": t.conference_losses,
        "ap_rank": t.ap_rank,
        "sp_rating": t.sp_rating,
        "season": t.season,
    }


@router.get("")
async def list_teams(
    conference: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    season: int = Query(2026),
    db: AsyncSession = Depends(get_db),
):
    query = select(Team).where(Team.season == season)
    if conference:
        query = query.where(Team.conference == conference)
    if search:
        query = query.where(Team.school.ilike(f"%{search}%"))
    query = query.order_by(Team.school)
    result = await db.execute(query)
    return [_team_dict(t) for t in result.scalars().all()]


@router.get("/{school}")
async def get_team(school: str, season: int = Query(2026), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.school == school, Team.season == season))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return _team_dict(team)
