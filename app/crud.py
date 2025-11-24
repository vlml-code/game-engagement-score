from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas


async def create_game(session: AsyncSession, game_in: schemas.GameCreate) -> models.Game:
    game = models.Game(**game_in.model_dump())
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return game


async def list_games(session: AsyncSession) -> list[models.Game]:
    result = await session.execute(
        select(models.Game).options(
            selectinload(models.Game.achievements),
            selectinload(models.Game.guides).selectinload(models.Guide.parsed_content),
            selectinload(models.Game.hltb_times),
            selectinload(models.Game.engagement_scores),
        )
    )
    return result.scalars().unique().all()


async def get_game_by_steam_app_id(
    session: AsyncSession, steam_app_id: int
) -> models.Game | None:
    result = await session.execute(
        select(models.Game).where(models.Game.steam_app_id == steam_app_id)
    )
    return result.scalar_one_or_none()


async def get_game(session: AsyncSession, game_id: int) -> models.Game | None:
    result = await session.execute(
        select(models.Game)
        .where(models.Game.id == game_id)
        .options(
            selectinload(models.Game.achievements),
            selectinload(models.Game.guides).selectinload(models.Guide.parsed_content),
            selectinload(models.Game.hltb_times),
            selectinload(models.Game.engagement_scores),
        )
    )
    return result.scalar_one_or_none()


async def update_game(
    session: AsyncSession, game: models.Game, game_in: schemas.GameUpdate
) -> models.Game:
    for key, value in game_in.model_dump(exclude_unset=True).items():
        setattr(game, key, value)
    await session.commit()
    await session.refresh(game)
    return game


async def delete_instance(session: AsyncSession, instance: models.Base) -> None:
    await session.delete(instance)
    await session.commit()


async def create_related(
    session: AsyncSession, model_cls: type[models.Base], data: dict
) -> models.Base:
    instance = model_cls(**data)
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return instance


async def add_achievements(
    session: AsyncSession, game_id: int, achievements: list[dict]
) -> int:
    existing = await session.execute(
        select(models.Achievement).where(models.Achievement.game_id == game_id)
    )
    existing_by_name = {ach.name: ach for ach in existing.scalars().all()}

    new_rows: list[models.Achievement] = []
    for achievement in achievements:
        name = achievement.get("name")
        if not name:
            continue
        if name in existing_by_name:
            existing_row = existing_by_name[name]
            updated = False
            for field in ("description", "points", "completion_rate"):
                value = achievement.get(field)
                if value is not None and getattr(existing_row, field) != value:
                    setattr(existing_row, field, value)
                    updated = True
            if updated:
                session.add(existing_row)
            continue

        new_rows.append(
            models.Achievement(
                game_id=game_id,
                name=name,
                description=achievement.get("description"),
                points=achievement.get("points"),
                completion_rate=achievement.get("completion_rate"),
            )
        )
    if new_rows:
        session.add_all(new_rows)

    await session.commit()
    return len(new_rows)


async def add_guides(session: AsyncSession, game_id: int, guides: list[dict]) -> int:
    existing = await session.execute(
        select(models.Guide.url).where(models.Guide.game_id == game_id)
    )
    existing_urls = {url for (url,) in existing.all() if url}

    new_rows: list[models.Guide] = []
    for guide in guides:
        url = guide.get("url")
        if url in existing_urls:
            continue
        new_rows.append(
            models.Guide(
                game_id=game_id,
                title=guide.get("title") or "Untitled Guide",
                url=url,
                author=guide.get("author"),
                created_at=guide.get("created_at"),
            )
        )

    if not new_rows:
        return 0

    session.add_all(new_rows)
    await session.commit()
    return len(new_rows)


async def list_related(
    session: AsyncSession, model_cls: type[models.Base], filter_field: str | None = None, value=None
) -> list[models.Base]:
    stmt = select(model_cls)
    if filter_field and value is not None:
        stmt = stmt.where(getattr(model_cls, filter_field) == value)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_related(
    session: AsyncSession, model_cls: type[models.Base], instance_id: int
) -> models.Base | None:
    result = await session.execute(select(model_cls).where(model_cls.id == instance_id))
    return result.scalar_one_or_none()


async def update_related(
    session: AsyncSession, instance: models.Base, payload: BaseModel
) -> models.Base:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(instance, key, value)
    await session.commit()
    await session.refresh(instance)
    return instance
