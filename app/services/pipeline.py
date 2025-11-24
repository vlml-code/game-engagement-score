import asyncio
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.config import Settings
from app.services.ai import AchievementAI, AchievementAIError
from app.services.guides import GuideParser, GuideParserError
from app.services.hltb import HLTBService, HLTBServiceError


@dataclass
class PipelineResult:
    game: models.Game
    main_story_achievement: models.Achievement | None = None
    hltb_hours: float | None = None
    engagement_score: float | None = None
    notes: list[str] = field(default_factory=list)


def engagement_score_formula(t_hours: float, completion_percent: float) -> float:
    C = max(0.01, min(completion_percent / 100.0, 0.99))
    T0 = 10.0
    ALPHA = 1.0
    BETA = 1.3
    SCALE = 400.0

    length_factor = (t_hours / (t_hours + T0)) ** ALPHA
    completion_factor = C ** BETA
    return SCALE * length_factor * completion_factor


async def _parse_guides_for_game(
    session: AsyncSession, game: models.Game, settings: Settings
) -> tuple[list[str], list[str]]:
    parser = GuideParser(
        request_interval=settings.guide_request_interval,
        steam_api_key=settings.steam_api_key,
    )
    parsed_texts: list[str] = []
    notes: list[str] = []
    try:
        first_guide = next((g for g in game.guides if g.url), None)
        if not first_guide:
            return parsed_texts, notes

        if first_guide.parsed_content:
            parsed_texts.extend([content.content for content in first_guide.parsed_content])
        else:
            await asyncio.sleep(settings.guide_request_interval)
            try:
                text, sections = await parser.fetch_and_parse(first_guide.url)
            except GuideParserError as exc:
                notes.append(f"Guide '{first_guide.title}' failed: {exc}")
            else:
                parsed = models.ParsedGuideContent(
                    guide_id=first_guide.id, content=text, section_count=sections
                )
                session.add(parsed)
                parsed_texts.append(text)
        await session.commit()
    finally:
        await parser.aclose()
    return parsed_texts, notes


async def _mark_main_story_completion(
    session: AsyncSession,
    game: models.Game,
    settings: Settings,
    guides_text: list[str],
) -> tuple[models.Achievement | None, list[str]]:
    notes: list[str] = []
    if not game.achievements:
        notes.append("No achievements to analyze.")
        return None, notes
    if not settings.openai_api_key:
        notes.append("OpenAI key missing; skipped main story detection.")
        return None, notes

    ai = AchievementAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        request_interval=settings.openai_request_interval,
    )
    payload_achievements = [
        {
            "name": ach.name,
            "description": ach.description,
            "completion_rate": ach.completion_rate,
        }
        for ach in game.achievements
    ]
    try:
        predicted_name = await ai.identify_main_story_achievement(
            game.title, payload_achievements, guides_text
        )
    except AchievementAIError as exc:
        notes.append(str(exc))
        return None, notes

    if not predicted_name:
        notes.append("No obvious main-story achievement detected.")
        return None, notes

    for ach in game.achievements:
        ach.is_main_story_completion = ach.name == predicted_name
        session.add(ach)
    await session.commit()

    main_story = next(
        (ach for ach in game.achievements if ach.is_main_story_completion), None
    )
    if main_story is None:
        notes.append("Model suggestion did not match stored achievements.")
    return main_story, notes


async def _fetch_hltb_time(
    game: models.Game, settings: Settings
) -> tuple[float | None, list[str]]:
    notes: list[str] = []
    service = HLTBService(request_interval=settings.hltb_request_interval)
    try:
        hours = await service.fetch_main_story_hours(game.title)
    except HLTBServiceError as exc:
        notes.append(str(exc))
        return None, notes

    if hours is None:
        notes.append("HowLongToBeat has no main-story time for this title.")
    return hours, notes


async def _upsert_hltb_time(
    session: AsyncSession, game: models.Game, main_story_hours: float | None
) -> None:
    result = await session.execute(
        models.HLTBTime.__table__.select().where(models.HLTBTime.game_id == game.id)
    )
    existing = result.fetchone()
    if existing:
        existing_id = existing._mapping["id"]
        await session.execute(
            models.HLTBTime.__table__.update()
            .where(models.HLTBTime.id == existing_id)
            .values(main_story_hours=main_story_hours)
        )
    else:
        session.add(models.HLTBTime(game_id=game.id, main_story_hours=main_story_hours))
    await session.commit()


async def analyze_game(
    session: AsyncSession, game: models.Game, settings: Settings
) -> PipelineResult:
    notes: list[str] = []
    guides_text, guide_notes = await _parse_guides_for_game(session, game, settings)
    notes.extend(guide_notes)

    main_story, ai_notes = await _mark_main_story_completion(
        session, game, settings, guides_text
    )
    notes.extend(ai_notes)

    hltb_hours, hltb_notes = await _fetch_hltb_time(game, settings)
    notes.extend(hltb_notes)
    await _upsert_hltb_time(session, game, hltb_hours)

    engagement: float | None = None
    if main_story and hltb_hours:
        completion_pct = main_story.completion_rate or 50.0
        if main_story.completion_rate is None:
            notes.append(
                "Using fallback 50% completion rate because Steam did not provide one."
            )
        engagement = engagement_score_formula(hltb_hours, completion_pct)
        score = models.EngagementScore(
            game_id=game.id,
            score=engagement,
            method="hltb_main_story + completion_rate",
            notes="; ".join(notes) if notes else None,
        )
        session.add(score)
        await session.commit()
    else:
        missing_bits = []
        if not main_story:
            missing_bits.append("main-story achievement")
        if not hltb_hours:
            missing_bits.append("HLTB main story time")
        notes.append("Cannot compute engagement score without " + " and ".join(missing_bits))
        score = models.EngagementScore(
            game_id=game.id,
            score=0.0,
            method="hltb_main_story + completion_rate",
            notes="; ".join(notes),
        )
        session.add(score)
        await session.commit()

    return PipelineResult(
        game=game,
        main_story_achievement=main_story,
        hltb_hours=hltb_hours,
        engagement_score=engagement,
        notes=notes,
    )
