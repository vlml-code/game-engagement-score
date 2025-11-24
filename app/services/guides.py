import asyncio
import logging
from collections.abc import Iterable
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup


class GuideParserError(Exception):
    """Raised when guide parsing fails."""


class GuideParser:
    def __init__(
        self,
        request_interval: float = 1.0,
        client: httpx.AsyncClient | None = None,
        steam_api_key: str | None = None,
    ) -> None:
        self.request_interval = max(request_interval, 0)
        self._last_request = 0.0
        self._lock = asyncio.Lock()
        self._client = client or httpx.AsyncClient(timeout=20)
        self._steam_api_key = steam_api_key
        self._logger = logging.getLogger(__name__)

    async def _throttle(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait_time = self.request_interval - (now - self._last_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = asyncio.get_event_loop().time()

    def _steam_file_id_from_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        if "steamcommunity.com" not in parsed.netloc:
            return None

        query_id = parse_qs(parsed.query).get("id", [])
        if query_id:
            return query_id[0]

        # Fallback for URLs like /sharedfiles/filedetails/1900225454
        parts = [p for p in parsed.path.split("/") if p]
        for idx, part in enumerate(parts):
            if part == "filedetails" and idx + 1 < len(parts):
                return parts[idx + 1].replace("?id=", "")
        return None

    async def _fetch_steam_details_html(self, file_id: str) -> str | None:
        if not self._steam_api_key:
            return None

        await self._throttle()
        try:
            response = await self._client.post(
                "https://api.steampowered.com/IPublishedFileService/GetDetails/v1/",
                data={
                    "key": self._steam_api_key,
                    "publishedfileids[0]": file_id,
                    "includemetadata": False,
                    "includechildren": False,
                },
            )
        except httpx.RequestError as exc:
            self._logger.warning(
                "Steam guide API request failed; falling back to HTML fetch",
                extra={"file_id": file_id, "error": str(exc)},
            )
            return None

        if response.status_code >= 400:
            self._logger.warning(
                "Steam guide API returned non-200; falling back to HTML fetch",
                extra={
                    "file_id": file_id,
                    "status": response.status_code,
                    "body": response.text[:200],
                },
            )
            return None

        payload = response.json().get("response", {})
        details = (payload.get("publishedfiledetails") or [])
        if not details:
            self._logger.warning(
                "Steam guide API returned no details; falling back to HTML fetch",
                extra={"file_id": file_id, "payload_keys": list(payload.keys())},
            )
            return None

        description = details[0].get("file_description") or details[0].get(
            "description"
        )
        if not description:
            self._logger.warning(
                "Steam guide API response missing description; falling back to HTML fetch",
                extra={"file_id": file_id, "available_keys": list(details[0].keys())},
            )
            return None

        return description

    async def fetch_html(self, url: str) -> str:
        steam_file_id = self._steam_file_id_from_url(url)
        if steam_file_id:
            html = await self._fetch_steam_details_html(steam_file_id)
            if html:
                return html

        await self._throttle()
        try:
            response = await self._client.get(url, follow_redirects=True)
        except httpx.RequestError as exc:
            raise GuideParserError(f"Failed to fetch guide: {exc}") from exc

        if response.status_code >= 400:
            raise GuideParserError(
                f"Guide request failed with status {response.status_code} for {url}"
            )

        return response.text

    @staticmethod
    def _text_from_elements(elements: Iterable) -> str:
        texts: list[str] = []
        for element in elements:
            text = element.get_text(" ", strip=True)
            if text:
                texts.append(text)
        return "\n\n".join(texts)

    def parse_html(self, html: str) -> tuple[str, int]:
        soup = BeautifulSoup(html, "html.parser")
        main_content = (
            soup.select_one("article")
            or soup.select_one("div#content")
            or soup.body
            or soup
        )
        if not main_content:
            raise GuideParserError("Could not locate content in guide HTML")

        paragraphs = main_content.find_all(["p", "li"])
        headings = main_content.find_all(["h1", "h2", "h3", "h4"])

        text = self._text_from_elements(paragraphs or [main_content])
        if not text:
            text = main_content.get_text(" ", strip=True)

        section_count = len(headings)
        return text, section_count

    async def fetch_and_parse(self, url: str) -> tuple[str, int]:
        html = await self.fetch_html(url)
        return self.parse_html(html)

    async def aclose(self) -> None:
        await self._client.aclose()
