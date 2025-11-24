from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AchievementBase(ORMBase):
    name: str
    description: Optional[str] = None
    points: Optional[int] = None
    completion_rate: Optional[float] = Field(
        default=None,
        description="Global completion percent for this achievement if available",
    )
    is_main_story_completion: bool = Field(
        default=False,
        description="Flag set when this represents finishing the main story",
    )


class AchievementCreate(AchievementBase):
    game_id: int


class AchievementUpdate(AchievementBase):
    pass


class AchievementRead(AchievementBase):
    id: int
    game_id: int

    model_config = ConfigDict(from_attributes=True)


class GuideBase(ORMBase):
    title: str
    url: Optional[str] = None
    author: Optional[str] = None


class GuideCreate(GuideBase):
    game_id: int


class GuideUpdate(GuideBase):
    pass


class GuideRead(GuideBase):
    id: int
    game_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParsedGuideContentBase(ORMBase):
    content: str
    section_count: Optional[int] = None


class ParsedGuideContentCreate(ParsedGuideContentBase):
    guide_id: int


class ParsedGuideContentUpdate(ParsedGuideContentBase):
    pass


class ParsedGuideContentRead(ParsedGuideContentBase):
    id: int
    guide_id: int

    model_config = ConfigDict(from_attributes=True)


class HLTBTimeBase(ORMBase):
    main_story_hours: Optional[float] = None
    extras_hours: Optional[float] = None
    completionist_hours: Optional[float] = None


class HLTBTimeCreate(HLTBTimeBase):
    game_id: int


class HLTBTimeUpdate(HLTBTimeBase):
    pass


class HLTBTimeRead(HLTBTimeBase):
    id: int
    game_id: int
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class EngagementScoreBase(ORMBase):
    score: float = Field(..., ge=0)
    method: Optional[str] = None
    notes: Optional[str] = None


class EngagementScoreCreate(EngagementScoreBase):
    game_id: int


class EngagementScoreUpdate(EngagementScoreBase):
    pass


class EngagementScoreRead(EngagementScoreBase):
    id: int
    game_id: int
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GameBase(ORMBase):
    title: str
    steam_app_id: Optional[int] = None
    genre: Optional[str] = None
    platform: Optional[str] = None
    release_date: Optional[str] = None
    description: Optional[str] = None


class GameCreate(GameBase):
    pass


class GameUpdate(GameBase):
    pass


class GameRead(GameBase):
    id: int
    created_at: datetime
    achievements: list[AchievementRead] = Field(default_factory=list)
    guides: list[GuideRead] = Field(default_factory=list)
    hltb_times: list[HLTBTimeRead] = Field(default_factory=list)
    engagement_scores: list[EngagementScoreRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SteamImportRequest(ORMBase):
    app_ids_text: str = Field(
        ..., description="Comma, whitespace, or newline-separated Steam app IDs"
    )


class SteamImportResult(ORMBase):
    app_id: int
    game_id: Optional[int] = None
    created_game: bool = False
    achievements_added: int = 0
    guides_added: int = 0
    guides_parsed: int = 0
    status: str
    error: Optional[str] = None


class SteamImportResponse(ORMBase):
    results: list[SteamImportResult]


class AnalysisResponse(ORMBase):
    game_id: int
    main_story_achievement: Optional[str] = None
    hltb_main_story_hours: Optional[float] = None
    engagement_score: Optional[float] = None
    notes: list[str] = Field(default_factory=list)
