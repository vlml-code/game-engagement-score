import asyncio
import logging
from typing import Any

from howlongtobeatpy import HowLongToBeat

logger = logging.getLogger(__name__)


class HLTBServiceError(Exception):
    """Raised when HowLongToBeat data cannot be retrieved."""


class HLTBService:
    def __init__(self, request_interval: float = 1.2) -> None:
        self.request_interval = max(request_interval, 0)
        self._last_request = 0.0
        self._lock = asyncio.Lock()
        self._client = HowLongToBeat()

    async def _throttle(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait_time = self.request_interval - (now - self._last_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = asyncio.get_event_loop().time()

    async def fetch_main_story_hours(self, title: str) -> float | None:
        await self._throttle()
        try:
            results: list[Any] | None = await asyncio.to_thread(
                self._client.search, title, similarity_case_sensitive=False
            )
        except Exception as exc:  # pragma: no cover - third-party exceptions vary
            raise HLTBServiceError(f"HLTB search failed: {exc}") from exc

        if not results:
            logger.warning("HLTB search returned no results", extra={"title": title})
            raise HLTBServiceError(
                f"HowLongToBeat returned no matches for '{title}' (case-insensitive search)"
            )

        best_match = max(results, key=lambda r: getattr(r, "similarity", 0))
        logger.info(
            "HLTB best match chosen",
            extra={
                "title": title,
                "match_name": getattr(best_match, "game_name", None),
                "similarity": getattr(best_match, "similarity", None),
                "main_story_minutes": getattr(best_match, "main_story", None),
            },
        )

        if getattr(best_match, "main_story", None) is None:
            raise HLTBServiceError(
                f"HowLongToBeat found '{getattr(best_match, 'game_name', None)}' but it lacks main-story time"
            )

        return float(best_match.main_story) / 60.0 if best_match.main_story else None
