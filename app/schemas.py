from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AchievementBase(BaseModel):
    name: str
    description: Optional[str] = None
    points: Optional[int] = None


class AchievementCreate(AchievementBase):
    game_id: int


class AchievementUpdate(AchievementBase):
    pass


class AchievementRead(AchievementBase):
    id: int
    game_id: int

    class Config:
        orm_mode = True


class GuideBase(BaseModel):
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

    class Config:
        orm_mode = True


class ParsedGuideContentBase(BaseModel):
    content: str
    section_count: Optional[int] = None


class ParsedGuideContentCreate(ParsedGuideContentBase):
    guide_id: int


class ParsedGuideContentUpdate(ParsedGuideContentBase):
    pass


class ParsedGuideContentRead(ParsedGuideContentBase):
    id: int
    guide_id: int

    class Config:
        orm_mode = True


class HLTBTimeBase(BaseModel):
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

    class Config:
        orm_mode = True


class EngagementScoreBase(BaseModel):
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

    class Config:
        orm_mode = True


class GameBase(BaseModel):
    title: str
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
    achievements: list[AchievementRead] = []
    guides: list[GuideRead] = []
    hltb_times: list[HLTBTimeRead] = []
    engagement_scores: list[EngagementScoreRead] = []

    class Config:
        orm_mode = True
