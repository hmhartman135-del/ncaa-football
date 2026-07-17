from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db
from ..services.analytics_service import get_leaderboard, METRIC_COLUMNS
from ..services.team_analytics_service import (
    get_team_full_stats, get_team_stat_rankings, generate_team_stats_analysis, TEAM_METRICS,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/metrics")
async def list_metrics():
    return METRIC_COLUMNS


@router.get("/team-metrics")
async def list_team_metrics():
    return [{"key": k, "label": v["label"], "better": v["better"]} for k, v in TEAM_METRICS.items()]


@router.get("/leaderboard")
async def leaderboard(
    metric: str = Query("passing_yards"),
    position: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await get_leaderboard(db, metric=metric, position=position, season=season, limit=limit)


@router.get("/team/{school}")
async def team_full_stats(school: str, season: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    data = await get_team_full_stats(db, school, season)
    if not data:
        raise HTTPException(status_code=404, detail="Team not found")
    return data


@router.get("/team/{school}/discuss")
async def team_stats_analysis(school: str, season: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    data = await generate_team_stats_analysis(db, school, season)
    if not data:
        raise HTTPException(status_code=404, detail="Team not found")
    return data


@router.get("/team-rankings")
async def team_rankings(
    metric: str = Query("offense_ppa"),
    season: Optional[int] = Query(None),
    conference: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_team_stat_rankings(db, metric, season=season, conference=conference)
