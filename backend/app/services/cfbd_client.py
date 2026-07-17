import httpx
from ..config import settings

BASE_URL = "https://api.collegefootballdata.com"


class CFBDClient:
    """Thin async wrapper around the CollegeFootballData.com API."""

    def __init__(self) -> None:
        self._headers = {
            "Authorization": f"Bearer {settings.cfbd_api_key}",
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: dict | None = None) -> list | dict:
        async with httpx.AsyncClient(base_url=BASE_URL, headers=self._headers, timeout=30) as client:
            resp = await client.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
            resp.raise_for_status()
            return resp.json()

    async def teams(self, year: int, classification: str = "fbs") -> list[dict]:
        return await self._get("/teams", {"year": year, "classification": classification})

    async def conferences(self) -> list[dict]:
        return await self._get("/conferences")

    async def games(self, year: int, season_type: str = "regular", week: int | None = None) -> list[dict]:
        return await self._get("/games", {"year": year, "seasonType": season_type, "week": week})

    async def rankings(self, year: int, season_type: str = "regular", week: int | None = None) -> list[dict]:
        return await self._get("/rankings", {"year": year, "seasonType": season_type, "week": week})

    async def team_records(self, year: int) -> list[dict]:
        return await self._get("/records", {"year": year})

    async def roster(self, year: int, team: str | None = None) -> list[dict]:
        return await self._get("/roster", {"year": year, "team": team})

    async def player_season_stats(self, year: int, season_type: str = "regular") -> list[dict]:
        return await self._get("/stats/player/season", {"year": year, "seasonType": season_type})

    async def player_ppa_season(self, year: int) -> list[dict]:
        return await self._get("/ppa/players/season", {"year": year})

    async def sp_ratings(self, year: int) -> list[dict]:
        return await self._get("/ratings/sp", {"year": year})

    async def recruiting_players(self, year: int) -> list[dict]:
        return await self._get("/recruiting/players", {"year": year})

    async def transfer_portal(self, year: int) -> list[dict]:
        return await self._get("/player/portal", {"year": year})

    async def draft_picks(self, year: int) -> list[dict]:
        return await self._get("/draft/picks", {"year": year})

    async def team_advanced_stats(self, year: int, team: str | None = None) -> list[dict]:
        return await self._get("/stats/season/advanced", {"year": year, "team": team})

    async def team_season_stats(self, year: int, team: str | None = None) -> list[dict]:
        return await self._get("/stats/season", {"year": year, "team": team})

    async def player_usage(self, year: int, team: str | None = None) -> list[dict]:
        return await self._get("/player/usage", {"year": year, "team": team})


cfbd = CFBDClient()
