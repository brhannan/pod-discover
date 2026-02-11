"""Pod-Discover REST API: FastAPI wrapper around existing logic."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import Database
from .models import ConsumptionEntry, TasteProfile
from .podcast_index import PodcastIndexClient
from .recommender import Recommender

db: Database
podcast_client: PodcastIndexClient
recommender: Recommender


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, podcast_client, recommender
    db = Database()
    podcast_client = PodcastIndexClient()
    recommender = Recommender(db, podcast_client)
    yield


app = FastAPI(title="Pod Discover", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Search & Discovery ---


@app.get("/api/episodes/search")
async def search_episodes(q: str, max_results: int = Query(default=10, le=50)):
    episodes = await podcast_client.search_episodes_by_term(q, max_results)
    return {"episodes": [ep.model_dump() for ep in episodes]}


@app.get("/api/episodes/random")
async def random_episodes(max_results: int = Query(default=5, le=20), category: str | None = None):
    episodes = await podcast_client.get_random_episodes(max_results, category)
    return {"episodes": [ep.model_dump() for ep in episodes]}


@app.get("/api/episodes/{episode_id}")
async def get_episode(episode_id: int):
    episode = await podcast_client.get_episode_by_id(episode_id)
    if not episode:
        return {"error": "Episode not found"}
    return episode.model_dump()


@app.get("/api/episodes/feed/{feed_id}")
async def get_feed_episodes(feed_id: int, max_results: int = Query(default=20, le=50)):
    episodes = await podcast_client.get_episodes_by_feed(feed_id, max_results)
    return {"episodes": [ep.model_dump() for ep in episodes]}


@app.get("/api/episodes/person/{person}")
async def search_by_person(person: str, max_results: int = Query(default=10, le=50)):
    episodes = await podcast_client.search_episodes_by_person(person, max_results)
    return {"episodes": [ep.model_dump() for ep in episodes]}


# --- Taste Profile ---


@app.get("/api/profile")
async def get_profile():
    return db.get_taste_profile().model_dump()


@app.put("/api/profile")
async def update_profile(profile: TasteProfile):
    current = db.get_taste_profile()
    updated_data = current.model_dump()
    updated_data.update(profile.model_dump(exclude_unset=True))
    updated_profile = TasteProfile(**updated_data)
    db.update_taste_profile(updated_profile)
    return updated_profile.model_dump()


# --- Feedback & History ---


class FeedbackRequest(BaseModel):
    item_id: str
    title: str
    rating: int = Field(ge=1, le=5)
    notes: str | None = None


@app.post("/api/feedback")
async def log_feedback(req: FeedbackRequest):
    entry = ConsumptionEntry(
        item_id=req.item_id,
        title=req.title,
        rating=req.rating,
        notes=req.notes,
    )
    entry_id = db.log_consumption(entry)
    return {"status": "success", "entry_id": entry_id}


@app.get("/api/history")
async def get_history(limit: int = Query(default=20, le=100)):
    history = db.get_consumption_history(limit)
    return {"entries": [entry.model_dump() for entry in history]}


# --- Favorite Podcasts ---


class FavoriteRequest(BaseModel):
    feed_id: int
    feed_title: str


@app.get("/api/favorites")
async def get_favorites():
    return {"favorites": db.get_favorite_feeds()}


@app.post("/api/favorites")
async def add_favorite(req: FavoriteRequest):
    db.add_favorite_feed(req.feed_id, req.feed_title)
    return {"status": "success"}


@app.delete("/api/favorites/{feed_id}")
async def remove_favorite(feed_id: int):
    db.remove_favorite_feed(feed_id)
    return {"status": "success"}


# --- AI Recommendations ---


class RecommendRequest(BaseModel):
    request: str = ""


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    result = await recommender.recommend(req.request)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
