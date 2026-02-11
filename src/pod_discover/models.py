from __future__ import annotations

from pydantic import BaseModel, Field


class Episode(BaseModel):
    id: int
    title: str
    description: str
    feed_title: str = ""
    feed_id: int | None = None
    duration_seconds: int | None = None
    date_published: str = ""
    url: str = ""
    image: str | None = None
    transcript_url: str | None = None


class TasteProfile(BaseModel):
    preferred_depth: str = "moderate"  # casual | moderate | deep-dive
    format_preferences: list[str] = Field(default_factory=list)  # narrative, interview, roundtable, solo
    topic_interests: dict[str, float] = Field(default_factory=dict)  # topic -> weight 0-1
    preferred_duration_min: int | None = None
    preferred_duration_max: int | None = None
    notes: str = ""


class ConsumptionEntry(BaseModel):
    id: int = 0
    item_type: str = "podcast_episode"
    item_id: str
    title: str
    rating: int = Field(ge=1, le=5)
    notes: str | None = None
    timestamp: str = ""


class QueueEntry(BaseModel):
    id: int = 0
    episode_id: int
    episode_title: str
    feed_id: int | None = None
    feed_title: str | None = None
    image: str | None = None
    url: str | None = None
    added_at: str = ""
