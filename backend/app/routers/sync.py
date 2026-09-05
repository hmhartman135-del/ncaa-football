"""
Refresh already-ingested CFBD data (team records, rosters, game scores,
recruiting, transfer portal) without duplicating rows — every ingest_*
function in data_ingestion.py upserts by a natural key, so this is safe to
run repeatedly, unlike the startup-only, empty-DB-gated _auto_ingest().

Manual: POST /sync/run queues a background sync and returns immediately;
GET /sync/status polls it. Automatic: main.py's lifespan calls
maybe_auto_sync() on startup, which only actually runs if the last sync is
more than 12h stale.
"""
import asyncio
import time
import logging
from fastapi import APIRouter, BackgroundTasks

from ..database import AsyncSessionLocal
from ..services.data_ingestion import (
    ingest_teams, ingest_games, ingest_rosters, ingest_season_stats,
    ingest_recruiting, ingest_transfer_portal,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["sync"])

_STALE_SECS = 12 * 3600
_lock = asyncio.Lock()
_state: dict = {
    "status": "idle",       # idle | running | error
    "last_run_ts": 0.0,
    "last_run_iso": None,
    "counts": {},
    "last_error": None,
}


async def _sync_all() -> None:
    if _lock.locked():
        return
    async with _lock:
        _state["status"] = "running"
        _state["last_error"] = None
        counts: dict = {}
        try:
            from ..main import SEASON, RECRUITING_CLASS, PORTAL_CYCLE  # deferred: avoid import cycle with main.py

            async with AsyncSessionLocal() as db:
                counts["teams"] = await ingest_teams(db, SEASON)
                counts["games"] = await ingest_games(db, SEASON)
                roster_count, roster_year = await ingest_rosters(db, SEASON)
                counts["rosters"] = roster_count
                counts["season_stats"] = await ingest_season_stats(db, roster_year)
                counts["recruiting"] = await ingest_recruiting(db, RECRUITING_CLASS)
                counts["transfer_portal"] = await ingest_transfer_portal(db, PORTAL_CYCLE)

            _state["status"] = "idle"
            _state["counts"] = counts
            _state["last_run_ts"] = time.time()
            _state["last_run_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            logger.info("Sync complete: %s", counts)
        except Exception as exc:
            _state["status"] = "error"
            _state["last_error"] = str(exc)
            logger.warning("Sync failed: %s", exc)


async def maybe_auto_sync() -> None:
    """Called from lifespan on startup — fires a background sync only if the
    last one is stale (or none has ever run), without blocking startup."""
    if (time.time() - _state["last_run_ts"]) > _STALE_SECS:
        asyncio.create_task(_sync_all())


@router.post("/run")
async def run_sync(background_tasks: BackgroundTasks):
    if _state["status"] == "running":
        return {"status": "already_running"}
    background_tasks.add_task(_sync_all)
    return {"status": "queued"}


@router.get("/status")
async def sync_status():
    age = time.time() - _state["last_run_ts"] if _state["last_run_ts"] else None
    return {
        **_state,
        "age_seconds": age,
        "is_stale": age is None or age > _STALE_SECS,
    }
