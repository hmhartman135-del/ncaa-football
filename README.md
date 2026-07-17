# NCAA Football Analytics Platform

FastAPI + Next.js NCAA D1 football platform. Data from [CollegeFootballData.com](https://collegefootballdata.com) (CFBD) + Claude AI for scouting, recruiting, transfer portal, and 2027 NFL Draft board.

Companion to `~/mlb-analytics`, `~/nba-analytics`, `~/ncaa-baseball`, `~/nfl-analytics`, `~/soccer-analytics`.

## Stack

- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis, Python 3.12
- Data source: [CollegeFootballData.com API](https://collegefootballdata.com/) (free, requires API key — get one at https://collegefootballdata.com/key)
- AI: Anthropic Claude (`claude-sonnet-4-6`) for scouting reports, recruiting/portal/draft grades
- Frontend: Next.js 14 + Tailwind + React Query

## Modules

- **Teams & Standings** — conference standings, AP/Coaches poll rankings
- **Players** — browse/filter D1 rosters
- **Analytics** — passing/rushing/receiving leaderboards, PPA, SP+ team ratings
- **Scouting** — AI scouting reports + player comparisons
- **Roster** — depth chart + AI roster-needs analysis
- **Recruiting** — 2027 signing class rankings
- **Transfer Portal** — 2026-27 cycle entries/commitments with AI grades
- **Draft Board** — 2027 NFL Draft prospects (real draft-eligible players, AI-graded)

## Ports

Postgres `5436`, Redis `6383`, backend `8004`, frontend `3004` (avoids conflicts with mlb 5432/6379/8000/3000, nba 5433/6380/8001, ncaa-baseball 5434/6381, nfl 5435/6382/3002, soccer 8003/3005).

## Setup

1. Get a free CFBD API key at https://collegefootballdata.com/key
2. `cp backend/.env.example backend/.env` and fill in `ANTHROPIC_API_KEY` and `CFBD_API_KEY`
3. `docker-compose up postgres redis -d`
4. Backend:
   ```
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8004
   ```
   First startup auto-ingests 2026 season teams/rosters/stats from CFBD (takes a minute).
5. Frontend:
   ```
   cd frontend
   npm install
   npm run dev
   ```
   Visit http://localhost:3004
