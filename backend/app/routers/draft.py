from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..services.draft_service import list_draft_eligible, get_or_create_prospect_grade, get_draft_board

router = APIRouter(prefix="/draft", tags=["draft"])


@router.get("/eligible")
async def eligible_players(
    season: Optional[int] = Query(None),
    position: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Real draft-eligible players from the roster, not AI-generated."""
    return await list_draft_eligible(db, season=season, position=position, limit=limit)


@router.get("/board")
async def draft_board(draft_year: int = Query(2027), db: AsyncSession = Depends(get_db)):
    prospects = await get_draft_board(db, draft_year=draft_year)
    return [
        {
            "player_id": p.player_id, "name": p.name, "position": p.position, "college": p.college,
            "class_year": p.class_year, "projected_round": p.projected_round, "grade": p.grade,
            "nfl_comparison": p.nfl_comparison, "ai_analysis": p.ai_analysis,
        }
        for p in prospects
    ]


@router.post("/grade/{player_id}")
async def grade_prospect(player_id: int, draft_year: int = Query(2027), db: AsyncSession = Depends(get_db)):
    prospect = await get_or_create_prospect_grade(db, player_id, draft_year)
    if not prospect:
        raise HTTPException(status_code=404, detail="Player not found")
    return {
        "player_id": prospect.player_id, "name": prospect.name, "position": prospect.position,
        "college": prospect.college, "class_year": prospect.class_year,
        "projected_round": prospect.projected_round, "grade": prospect.grade,
        "nfl_comparison": prospect.nfl_comparison, "ai_analysis": prospect.ai_analysis,
    }
