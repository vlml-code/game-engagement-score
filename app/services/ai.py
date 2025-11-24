import asyncio
from typing import Iterable

from openai import AsyncOpenAI, OpenAIError


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
        guide_snippets = []
        for text in guides:
            snippet = text.strip()
            if not snippet:
                continue
            guide_snippets.append(snippet[:800])
            if len(guide_snippets) >= 3:
                break

        achievement_lines = []
        for ach in achievements:
            line = f"- {ach.get('name')}: {ach.get('description') or 'No description'}"
            rate = ach.get("completion_rate")
            if rate is not None:
                line += f" (global completion {rate:.2f}%)"
            achievement_lines.append(line)

        system_prompt = (
            "You are helping mark the achievement that corresponds to finishing the main story/campaign. "
            "Only reply with the exact achievement name. If none of the achievements clearly indicate "
            "main story completion, respond with NONE."
        )

        user_prompt = (
            "Game title: "
            f"{game_title}\n\nAchievements:\n" + "\n".join(achievement_lines)
        )
        if guide_snippets:
            user_prompt += "\n\nGuide excerpts to help you decide:\n" + "\n---\n".join(
                guide_snippets
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_tokens=20,
            )
        except OpenAIError as exc:
            raise AchievementAIError(f"OpenAI request failed: {exc}") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            return None

        cleaned = content.strip().splitlines()[0].strip('" ')
        if cleaned.upper() == "NONE":
            return None
        return cleaned
