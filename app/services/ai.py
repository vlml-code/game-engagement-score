import asyncio
import json
import logging
from typing import Iterable, Sequence

from openai import AsyncOpenAI, OpenAIError


logger = logging.getLogger(__name__)


class AchievementAIError(Exception):
    """Raised when the OpenAI analysis fails."""


class AchievementAI:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        request_interval: float = 2.0,
    ) -> None:
        if not api_key:
            raise AchievementAIError("OpenAI API key is not configured")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.request_interval = max(request_interval, 0)
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def _throttle(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait_time = self.request_interval - (now - self._last_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request = asyncio.get_event_loop().time()

    async def identify_main_story_achievement(
        self,
        game_title: str,
        achievements: Iterable[dict],
        guides: Iterable[str],
    ) -> str | None:
        await self._throttle()

        guide_text = next((text.strip() for text in guides if text.strip()), "")

        achievement_lines = []
        for ach in achievements:
            line = f"- {ach.get('name')}: {ach.get('description') or 'No description'}"
            rate = ach.get("completion_rate")
            if rate is not None:
                line += f" (global completion {rate:.2f}%)"
            achievement_lines.append(line)

        system_prompt = (
            "You label the single achievement that marks completing the main story/campaign. "
            "Respond ONLY with that exact achievement name. If no achievement clearly represents "
            "finishing the main story, reply with NONE. Do not add quotes or any extra text."
        )

        user_sections = [
            f"Game title: {game_title}",
            "Achievements:",
            "\n".join(achievement_lines),
        ]
        if guide_text:
            user_sections.append("Guide content (first guide only):")
            user_sections.append(guide_text)
        user_prompt = "\n\n".join(user_sections)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        request_payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 1,
            "max_completion_tokens": 200,
        }
        logger.info(
            "Sending OpenAI request for main-story detection: %s",
            json.dumps(request_payload, ensure_ascii=False),
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=1,
                # Some newer models reject `max_tokens`; use `max_completion_tokens` instead.
                max_completion_tokens=200,
            )
        except OpenAIError as exc:
            raise AchievementAIError(f"OpenAI request failed: {exc}") from exc

        response_payload = response.model_dump()
        logger.info(
            "Received OpenAI response for main-story detection: %s",
            json.dumps(response_payload, ensure_ascii=False),
        )

        def _extract_content(message_content: str | Sequence[dict] | None) -> str:
            if isinstance(message_content, str):
                return message_content
            if isinstance(message_content, Sequence):
                parts: list[str] = []
                for item in message_content:
                    if isinstance(item, dict):
                        text = item.get("text") or ""
                        parts.append(str(text))
                return "".join(parts)
            return ""

        content = ""
        if response.choices:
            content = _extract_content(response.choices[0].message.content)

        content = content.strip()
        if not content:
            logger.warning(
                "OpenAI response missing content (finish_reason=%s)",
                response.choices[0].finish_reason if response.choices else "<none>",
            )
            return None

        cleaned = content.splitlines()[0].strip('" ')
        if cleaned.upper() == "NONE":
            return None
        return cleaned
