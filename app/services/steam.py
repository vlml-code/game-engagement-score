import asyncio
import time
from datetime import datetime
from typing import Any

import httpx


class SteamServiceError(Exception):
    """Raised when the Steam service encounters an error."""


class SteamService:
    def __init__(
        self,
        api_key: str,
        request_interval: float = 0.35,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise SteamServiceError("Steam API key is missing or not configured")
        self.api_key = api_key
        self.request_interval = max(request_interval, 0)
        self._client = client or httpx.AsyncClient(timeout=15)
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "SteamService":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait_time = self.request_interval - (now - self._last_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = time.monotonic()

    async def fetch_global_achievement_percentages(
        self, app_id: int
    ) -> dict[str, float]:
        await self._throttle()
        params = {"gameid": app_id}
        url = (
            "https://api.steampowered.com/ISteamUserStats/"
            "GetGlobalAchievementPercentagesForApp/v0002/"
        )
        response = await self._client.get(url, params=params)
        if response.status_code >= 400:
            raise SteamServiceError(
                f"Steam achievement percentages failed for app {app_id} with status {response.status_code}"
            )

        payload = response.json()
        achievements = (
            payload.get("achievementpercentages", {}).get("achievements", [])
        )
        return {
            item.get("name"): float(item.get("percent", 0))
            for item in achievements
            if item.get("name")
        }

    async def fetch_achievements(self, app_id: int) -> dict[str, Any]:
        await self._throttle()
        params = {"key": self.api_key, "appid": app_id}
        url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
        response = await self._client.get(url, params=params)
        if response.status_code >= 400:
            raise SteamServiceError(
                f"Steam achievements request failed for app {app_id} with status {response.status_code}"
            )

        payload = response.json()
        game = payload.get("game") or payload.get("game", {})
        if not game:
            raise SteamServiceError(f"Missing game schema for app {app_id}")

        game_name = game.get("gameName")
        stats = game.get("availableGameStats", {})
        achievements = stats.get("achievements", [])
        try:
            percents = await self.fetch_global_achievement_percentages(app_id)
        except SteamServiceError:
            percents = {}
        parsed = [
            {
                "name": item.get("displayName") or item.get("name"),
                "description": item.get("description"),
                "points": item.get("defaultvalue"),
                "completion_rate": percents.get(item.get("name")),
            }
            for item in achievements
            if item.get("displayName") or item.get("name")
        ]

        if not parsed:
            raise SteamServiceError(f"No achievements returned for app {app_id}")

        return {"game_name": game_name, "achievements": parsed}

    async def fetch_guides(self, app_id: int) -> list[dict[str, Any]]:
        await self._throttle()
        url = "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"
        params = {
            "key": self.api_key,
            "appid": app_id,
            "page": 1,
            "return_short_description": True,
            "numperpage": 20,
            "requiredtags[0]": "guides",
        }
        response = await self._client.get(url, params=params)
        if response.status_code >= 400:
            raise SteamServiceError(
                f"Steam guides request failed for app {app_id} with status {response.status_code}"
            )

        data = response.json()
        files = data.get("response", {}).get("publishedfiledetails", [])
        guides: list[dict[str, Any]] = []

        for guide in files:
            file_id = guide.get("publishedfileid")
            title = guide.get("title")
            if not file_id or not title:
                continue
            created_at = guide.get("time_created")
            created = (
                datetime.utcfromtimestamp(created_at)
                if isinstance(created_at, (int, float)) and created_at > 0
                else None
            )
            guides.append(
                {
                    "title": title,
                    "url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={file_id}",
                    "author": guide.get("creator") or guide.get("creator_app_id"),
                    "created_at": created,
                }
            )

        if not guides:
            raise SteamServiceError(f"No guides returned for app {app_id}")

        return guides
