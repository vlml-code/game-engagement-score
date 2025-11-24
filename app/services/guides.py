import asyncio
from collections.abc import Iterable

import httpx
from bs4 import BeautifulSoup


class GuideParserError(Exception):
    """Raised when guide parsing fails."""


class GuideParser:
    def __init__(
        self,
        request_interval: float = 1.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.request_interval = max(request_interval, 0)
        self._last_request = 0.0
        self._lock = asyncio.Lock()
        self._client = client or httpx.AsyncClient(timeout=20)

    async def _throttle(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait_time = self.request_interval - (now - self._last_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = asyncio.get_event_loop().time()

    async def fetch_html(self, url: str) -> str:
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
