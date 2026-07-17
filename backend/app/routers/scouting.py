from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.scouting_service import generate_scouting_report, compare_players

router = APIRouter(prefix="/scouting", tags=["scouting"])


class CompareRequest(BaseModel):
    player_ids: list[int]
    team_context: str | None = None


@router.get("/report/{player_id}")
async def scouting_report(player_id: int, db: AsyncSession = Depends(get_db)):
    report = await generate_scouting_report(db, player_id)
    return {"player_id": player_id, "report": report}


@router.post("/compare")
async def compare(req: CompareRequest, db: AsyncSession = Depends(get_db)):
    analysis = await compare_players(db, req.player_ids, req.team_context)
    return {"player_ids": req.player_ids, "team_context": req.team_context, "analysis": analysis}
