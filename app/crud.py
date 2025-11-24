from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas


async def create_game(session: AsyncSession, game_in: schemas.GameCreate) -> models.Game:
    game = models.Game(**game_in.dict())
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
    for key, value in game_in.dict(exclude_unset=True).items():
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
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(instance, key, value)
    await session.commit()
    await session.refresh(instance)
    return instance
