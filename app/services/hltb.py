import asyncio
from typing import Any

from howlongtobeatpy import HowLongToBeat


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
                self._client.search, title
            )
        except Exception as exc:  # pragma: no cover - third-party exceptions vary
            raise HLTBServiceError(f"HLTB search failed: {exc}") from exc

        if not results:
            return None

        best_match = max(results, key=lambda r: getattr(r, "similarity", 0))
        if getattr(best_match, "main_story", None) is None:
            return None
        return float(best_match.main_story) / 60.0 if best_match.main_story else None
