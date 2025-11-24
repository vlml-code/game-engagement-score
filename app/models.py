from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    steam_app_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(120))
    platform: Mapped[str | None] = mapped_column(String(120))
    release_date: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    achievements: Mapped[list["Achievement"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    guides: Mapped[list["Guide"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    hltb_times: Mapped[list["HLTBTime"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    engagement_scores: Mapped[list["EngagementScore"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int | None] = mapped_column(Integer)
    completion_rate: Mapped[float | None] = mapped_column(Float)
    is_main_story_completion: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    game: Mapped[Game] = relationship(back_populates="achievements")


class Guide(Base):
    __tablename__ = "guides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    game: Mapped[Game] = relationship(back_populates="guides")
    parsed_content: Mapped[list["ParsedGuideContent"]] = relationship(
        back_populates="guide", cascade="all, delete-orphan"
    )


class ParsedGuideContent(Base):
    __tablename__ = "parsed_guide_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guide_id: Mapped[int] = mapped_column(ForeignKey("guides.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section_count: Mapped[int | None] = mapped_column(Integer)

    guide: Mapped[Guide] = relationship(back_populates="parsed_content")


class HLTBTime(Base):
    __tablename__ = "hltb_times"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    main_story_hours: Mapped[float | None] = mapped_column(Float)
    extras_hours: Mapped[float | None] = mapped_column(Float)
    completionist_hours: Mapped[float | None] = mapped_column(Float)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    game: Mapped[Game] = relationship(back_populates="hltb_times")


class EngagementScore(Base):
    __tablename__ = "engagement_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str | None] = mapped_column(String(120))
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    game: Mapped[Game] = relationship(back_populates="engagement_scores")
