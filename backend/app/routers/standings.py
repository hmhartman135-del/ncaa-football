from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models.team import Team

router = APIRouter(prefix="/standings", tags=["standings"])


@router.get("")
async def get_standings(season: int = Query(2026), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.season == season))
    teams = result.scalars().all()

    grouped: dict[str, list[dict]] = {}
    for t in teams:
        conf = t.conference or "Independent"
        win_pct = (t.wins or 0) / max((t.wins or 0) + (t.losses or 0), 1)
        grouped.setdefault(conf, []).append({
            "school": t.school,
            "mascot": t.mascot,
            "logo": t.logo,
            "wins": t.wins or 0,
            "losses": t.losses or 0,
            "conference_wins": t.conference_wins or 0,
            "conference_losses": t.conference_losses or 0,
            "ap_rank": t.ap_rank,
            "sp_rating": t.sp_rating,
            "win_pct": round(win_pct, 3),
        })

    for conf in grouped:
        grouped[conf].sort(key=lambda x: -x["win_pct"])

    return dict(sorted(grouped.items()))


@router.get("/rankings")
async def get_rankings(season: int = Query(2026), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Team).where(Team.season == season, Team.ap_rank.isnot(None)).order_by(Team.ap_rank)
    )
    teams = result.scalars().all()
    return [
        {"rank": t.ap_rank, "school": t.school, "conference": t.conference,
         "record": f"{t.wins or 0}-{t.losses or 0}", "logo": t.logo}
        for t in teams
    ]
