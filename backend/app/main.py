from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .config import settings
from .routers import teams, standings, players, analytics, scouting, roster, recruiting, transfer, draft, games, rankings

SEASON = 2026  # Most recent/current college football season (2026 offseason -> in-season as year progresses)
RECRUITING_CLASS = 2026  # signing class CFBD actually has data for right now (2027 class hasn't started committing in bulk)
PORTAL_CYCLE = 2026  # transfer cycle feeding the 2026 season — CFBD has no 2027 portal data yet
DRAFT_CLASS = 2027


async def _auto_ingest():
    """Ingest CFBD data on startup if the DB is empty."""
    from .database import AsyncSessionLocal
    from .services.data_ingestion import (
        ingest_teams, ingest_rosters, ingest_season_stats,
        ingest_recruiting, ingest_transfer_portal, ingest_games, ingest_draft_picks,
    )
    from sqlalchemy import text

    if not settings.cfbd_api_key:
        print("[startup] CFBD_API_KEY not set — skipping auto-ingest. Add it to backend/.env.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM teams"))
        count = result.scalar()
        if count:
            print(f"[startup] Found {count} teams in DB — skipping auto-ingest.")
            return

        print(f"[startup] No data found — ingesting {SEASON} season from CFBD...")
        try:
            await ingest_teams(db, SEASON)
            await ingest_teams(db, SEASON - 1)  # last season's final record, for "how'd they do last year"
            _, roster_year = await ingest_rosters(db, SEASON)
            await ingest_season_stats(db, roster_year)
            await ingest_recruiting(db, RECRUITING_CLASS)
            await ingest_transfer_portal(db, PORTAL_CYCLE)
            await ingest_games(db, SEASON)
            await ingest_draft_picks(db, SEASON)  # players who left for the NFL after the roster_year season
            print("[startup] Ingestion complete.")
        except Exception as exc:
            print(f"[startup] Ingestion failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _auto_ingest()
    yield


app = FastAPI(title="NCAA Football Analytics API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")] + ["http://localhost:3004"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(teams.router)
app.include_router(standings.router)
app.include_router(players.router)
app.include_router(analytics.router)
app.include_router(scouting.router)
app.include_router(roster.router)
app.include_router(recruiting.router)
app.include_router(transfer.router)
app.include_router(draft.router)
app.include_router(games.router)
app.include_router(rankings.router)


@app.get("/health")
async def health():
    """Intentionally does NOT touch the database — always responds immediately."""
    return {"status": "ok", "service": "NCAA Football Analytics Platform"}


@app.get("/healthz")
async def healthz():
    """Kubernetes-style alias — also DB-free."""
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "message": "NCAA Football Analytics API",
        "version": "0.1.0",
        "season": SEASON,
        "recruiting_class": RECRUITING_CLASS,
        "draft_class": DRAFT_CLASS,
        "health": "/health",
        "note": "Open the Vercel frontend URL to use the app — this is the API backend only.",
    }


@app.post("/admin/ingest")
async def manual_ingest():
    await _auto_ingest()
    return {"status": "ok"}
