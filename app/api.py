from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.config import get_settings
from app.db import get_session
from app.services import pipeline
from app.services.steam import SteamService, SteamServiceError

router = APIRouter()


@router.post("/games", response_model=schemas.GameRead, status_code=status.HTTP_201_CREATED)
async def create_game(game_in: schemas.GameCreate, session: AsyncSession = Depends(get_session)):
    return await crud.create_game(session, game_in)


@router.get("/games", response_model=list[schemas.GameRead])
async def read_games(session: AsyncSession = Depends(get_session)):
    return await crud.list_games(session)


@router.get("/games/{game_id}", response_model=schemas.GameRead)
async def read_game(game_id: int, session: AsyncSession = Depends(get_session)):
    game = await crud.get_game(session, game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return game


@router.put("/games/{game_id}", response_model=schemas.GameRead)
async def update_game(game_id: int, game_in: schemas.GameUpdate, session: AsyncSession = Depends(get_session)):
    game = await crud.get_game(session, game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return await crud.update_game(session, game, game_in)


@router.delete("/games/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(game_id: int, session: AsyncSession = Depends(get_session)):
    game = await crud.get_game(session, game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    await crud.delete_instance(session, game)


async def _get_related_or_404(
    session: AsyncSession, model_cls: type[models.Base], instance_id: int
):
    instance = await crud.get_related(session, model_cls, instance_id)
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return instance


@router.post("/achievements", response_model=schemas.AchievementRead, status_code=status.HTTP_201_CREATED)
async def create_achievement(
    achievement_in: schemas.AchievementCreate, session: AsyncSession = Depends(get_session)
):
    await _get_related_or_404(session, models.Game, achievement_in.game_id)
    created = await crud.create_related(session, models.Achievement, achievement_in.dict())
    return created


@router.get("/achievements", response_model=list[schemas.AchievementRead])
async def read_achievements(session: AsyncSession = Depends(get_session)):
    return await crud.list_related(session, models.Achievement)


@router.get("/achievements/{achievement_id}", response_model=schemas.AchievementRead)
async def read_achievement(achievement_id: int, session: AsyncSession = Depends(get_session)):
    achievement = await _get_related_or_404(session, models.Achievement, achievement_id)
    return achievement


@router.put("/achievements/{achievement_id}", response_model=schemas.AchievementRead)
async def update_achievement(
    achievement_id: int,
    achievement_in: schemas.AchievementUpdate,
    session: AsyncSession = Depends(get_session),
):
    achievement = await _get_related_or_404(session, models.Achievement, achievement_id)
    return await crud.update_related(session, achievement, achievement_in)


@router.delete("/achievements/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(achievement_id: int, session: AsyncSession = Depends(get_session)):
    achievement = await _get_related_or_404(session, models.Achievement, achievement_id)
    await crud.delete_instance(session, achievement)


@router.post("/guides", response_model=schemas.GuideRead, status_code=status.HTTP_201_CREATED)
async def create_guide(guide_in: schemas.GuideCreate, session: AsyncSession = Depends(get_session)):
    await _get_related_or_404(session, models.Game, guide_in.game_id)
    return await crud.create_related(session, models.Guide, guide_in.dict())


@router.get("/guides", response_model=list[schemas.GuideRead])
async def read_guides(session: AsyncSession = Depends(get_session)):
    return await crud.list_related(session, models.Guide)


@router.get("/guides/{guide_id}", response_model=schemas.GuideRead)
async def read_guide(guide_id: int, session: AsyncSession = Depends(get_session)):
    guide = await _get_related_or_404(session, models.Guide, guide_id)
    return guide


@router.put("/guides/{guide_id}", response_model=schemas.GuideRead)
async def update_guide(
    guide_id: int, guide_in: schemas.GuideUpdate, session: AsyncSession = Depends(get_session)
):
    guide = await _get_related_or_404(session, models.Guide, guide_id)
    return await crud.update_related(session, guide, guide_in)


@router.delete("/guides/{guide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guide(guide_id: int, session: AsyncSession = Depends(get_session)):
    guide = await _get_related_or_404(session, models.Guide, guide_id)
    await crud.delete_instance(session, guide)


@router.post(
    "/parsed-content", response_model=schemas.ParsedGuideContentRead, status_code=status.HTTP_201_CREATED
)
async def create_parsed_content(
    parsed_in: schemas.ParsedGuideContentCreate, session: AsyncSession = Depends(get_session)
):
    await _get_related_or_404(session, models.Guide, parsed_in.guide_id)
    return await crud.create_related(session, models.ParsedGuideContent, parsed_in.dict())


@router.get("/parsed-content", response_model=list[schemas.ParsedGuideContentRead])
async def read_parsed_content(session: AsyncSession = Depends(get_session)):
    return await crud.list_related(session, models.ParsedGuideContent)


@router.get("/parsed-content/{content_id}", response_model=schemas.ParsedGuideContentRead)
async def read_parsed_content_item(content_id: int, session: AsyncSession = Depends(get_session)):
    return await _get_related_or_404(session, models.ParsedGuideContent, content_id)


@router.put("/parsed-content/{content_id}", response_model=schemas.ParsedGuideContentRead)
async def update_parsed_content(
    content_id: int,
    parsed_in: schemas.ParsedGuideContentUpdate,
    session: AsyncSession = Depends(get_session),
):
    content = await _get_related_or_404(session, models.ParsedGuideContent, content_id)
    return await crud.update_related(session, content, parsed_in)


@router.delete("/parsed-content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parsed_content(content_id: int, session: AsyncSession = Depends(get_session)):
    content = await _get_related_or_404(session, models.ParsedGuideContent, content_id)
    await crud.delete_instance(session, content)


@router.post("/hltb-times", response_model=schemas.HLTBTimeRead, status_code=status.HTTP_201_CREATED)
async def create_hltb_time(time_in: schemas.HLTBTimeCreate, session: AsyncSession = Depends(get_session)):
    await _get_related_or_404(session, models.Game, time_in.game_id)
    return await crud.create_related(session, models.HLTBTime, time_in.dict())


@router.get("/hltb-times", response_model=list[schemas.HLTBTimeRead])
async def read_hltb_times(session: AsyncSession = Depends(get_session)):
    return await crud.list_related(session, models.HLTBTime)


@router.get("/hltb-times/{time_id}", response_model=schemas.HLTBTimeRead)
async def read_hltb_time(time_id: int, session: AsyncSession = Depends(get_session)):
    return await _get_related_or_404(session, models.HLTBTime, time_id)


@router.put("/hltb-times/{time_id}", response_model=schemas.HLTBTimeRead)
async def update_hltb_time(
    time_id: int, time_in: schemas.HLTBTimeUpdate, session: AsyncSession = Depends(get_session)
):
    time_entry = await _get_related_or_404(session, models.HLTBTime, time_id)
    return await crud.update_related(session, time_entry, time_in)


@router.delete("/hltb-times/{time_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hltb_time(time_id: int, session: AsyncSession = Depends(get_session)):
    time_entry = await _get_related_or_404(session, models.HLTBTime, time_id)
    await crud.delete_instance(session, time_entry)


@router.post(
    "/engagement-scores",
    response_model=schemas.EngagementScoreRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_engagement_score(
    score_in: schemas.EngagementScoreCreate, session: AsyncSession = Depends(get_session)
):
    await _get_related_or_404(session, models.Game, score_in.game_id)
    return await crud.create_related(session, models.EngagementScore, score_in.dict())


@router.get("/engagement-scores", response_model=list[schemas.EngagementScoreRead])
async def read_engagement_scores(session: AsyncSession = Depends(get_session)):
    return await crud.list_related(session, models.EngagementScore)


def _parse_app_ids(app_ids_text: str) -> list[int]:
    tokens = [token.strip() for token in app_ids_text.replace("\n", ",").split(",")]
    app_ids: list[int] = []
    for token in tokens:
        if not token:
            continue
        try:
            app_ids.append(int(token))
        except ValueError:
            continue
    return list(dict.fromkeys(app_ids))


@router.post("/steam/import", response_model=schemas.SteamImportResponse)
async def import_from_steam(
    payload: schemas.SteamImportRequest, session: AsyncSession = Depends(get_session)
):
    settings = get_settings()
    if not settings.steam_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Steam API key is not configured",
        )

    app_ids = _parse_app_ids(payload.app_ids_text)
    if not app_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid Steam app IDs were provided",
        )

    results: list[schemas.SteamImportResult] = []

    async with SteamService(
        api_key=settings.steam_api_key, request_interval=settings.steam_request_interval
    ) as steam:
        for app_id in app_ids:
            created_game = False
            achievements_added = 0
            guides_added = 0
            status_message = "ok"
            error_message: str | None = None

            try:
                schema = await steam.fetch_achievements(app_id)
            except SteamServiceError as exc:
                results.append(
                    schemas.SteamImportResult(
                        app_id=app_id,
                        status="error",
                        error=str(exc),
                    )
                )
                continue

            game = await crud.get_game_by_steam_app_id(session, app_id)
            if not game:
                game = await crud.create_game(
                    session,
                    schemas.GameCreate(
                        title=schema.get("game_name") or f"App {app_id}",
                        steam_app_id=app_id,
                        description="Imported from Steam",
                    ),
                )
                created_game = True

            achievements_added = await crud.add_achievements(
                session, game.id, schema.get("achievements", [])
            )

            try:
                guides = await steam.fetch_guides(app_id)
                guides_added = await crud.add_guides(session, game.id, guides)
            except SteamServiceError as exc:
                status_message = "partial"
                error_message = str(exc)

            results.append(
                schemas.SteamImportResult(
                    app_id=app_id,
                    game_id=game.id,
                    created_game=created_game,
                    achievements_added=achievements_added,
                    guides_added=guides_added,
                    status=status_message,
                    error=error_message,
                )
            )

    return schemas.SteamImportResponse(results=results)


@router.post(
    "/games/{game_id}/analyze", response_model=schemas.AnalysisResponse
)
async def analyze_game(
    game_id: int, session: AsyncSession = Depends(get_session)
):
    game = await crud.get_game(session, game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    result = await pipeline.analyze_game(session, game, get_settings())
    return schemas.AnalysisResponse(
        game_id=game_id,
        main_story_achievement=(
            result.main_story_achievement.name if result.main_story_achievement else None
        ),
        hltb_main_story_hours=result.hltb_hours,
        engagement_score=result.engagement_score,
        notes=result.notes,
    )


@router.get("/engagement-scores/{score_id}", response_model=schemas.EngagementScoreRead)
async def read_engagement_score(score_id: int, session: AsyncSession = Depends(get_session)):
    return await _get_related_or_404(session, models.EngagementScore, score_id)


@router.put("/engagement-scores/{score_id}", response_model=schemas.EngagementScoreRead)
async def update_engagement_score(
    score_id: int,
    score_in: schemas.EngagementScoreUpdate,
    session: AsyncSession = Depends(get_session),
):
    score_entry = await _get_related_or_404(session, models.EngagementScore, score_id)
    return await crud.update_related(session, score_entry, score_in)


@router.delete("/engagement-scores/{score_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement_score(score_id: int, session: AsyncSession = Depends(get_session)):
    score_entry = await _get_related_or_404(session, models.EngagementScore, score_id)
    await crud.delete_instance(session, score_entry)
