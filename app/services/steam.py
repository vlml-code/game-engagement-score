import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


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
        # Steam Web API uses filetype 10 for "All Guides" (per IPublishedFileService docs).
        # Some games only respond to the broader web guide type (11), and others may omit the
        # Guide tag entirely. Try a few variants to maximise coverage.
        request_variants = [
            {
                "label": "all_guides_tagged",
                "params": {
                    "filetype": 10,  # k_PFI_MatchingFileType_AllGuides
                    "requiredtags[0]": "Guide",
                },
            },
            {
                "label": "all_guides_untagged",
                "params": {
                    "filetype": 10,
                },
            },
            {
                "label": "web_guides_tagged",
                "params": {
                    "filetype": 11,  # k_PFI_MatchingFileType_WebGuides
                    "requiredtags[0]": "Guide",
                },
            },
            {
                "label": "web_guides_untagged",
                "params": {
                    "filetype": 11,
                },
            },
        ]

        guides: list[dict[str, Any]] = []
        last_files: list[dict[str, Any]] | None = None
        last_params: dict[str, Any] | None = None

        for variant in request_variants:
            params = {
                "key": self.api_key,
                "appid": app_id,
                "page": 1,
                "return_short_description": True,
                "numperpage": 50,
                "return_vote_data": True,
                "strip_description_bbcode": True,
                **variant["params"],
            }
            response = await self._client.get(url, params=params)
            if response.status_code >= 400:
                raise SteamServiceError(
                    f"Steam guides request failed for app {app_id} with status {response.status_code}"
                )

            data = response.json()
            files = data.get("response", {}).get("publishedfiledetails", [])
            last_files, last_params = files, params
            logger.info(
                "Steam guides response received",
                extra={
                    "app_id": app_id,
                    "result_count": data.get("response", {}).get("resultcount"),
                    "file_count": len(files),
                    "variant": variant["label"],
                    "params": params,
                },
            )

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

            if guides:
                break

        if not guides:
            first_file = (last_files or [None])[0]
            logger.warning(
                "No guides parsed from Steam response",
                extra={
                    "app_id": app_id,
                    "file_count": len(last_files) if last_files else 0,
                    "first_file_keys": list(first_file.keys()) if isinstance(first_file, dict) else None,
                    "last_params": last_params,
                },
            )
            raise SteamServiceError(
                f"No guides returned for app {app_id}; request params {last_params}"
            )

        return guides
