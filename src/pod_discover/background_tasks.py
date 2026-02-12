"""Background tasks for cache refresh"""

import asyncio
import logging

from .config import REDDIT_SUBREDDITS
from .db import Database
from .podcast_index import PodcastIndexClient
from .reddit_parser import RedditParser

logger = logging.getLogger(__name__)


async def refresh_trending_cache(db: Database, podcast_client: PodcastIndexClient):
    """Refresh trending podcasts and episodes cache"""
    try:
        logger.info("Refreshing trending cache...")

        # Fetch trending podcasts
        trending_podcasts = await podcast_client.get_trending_podcasts(max=100)

        # Try to fetch trending episodes (may not be available on all API versions)
        episodes_dict = {}
        try:
            trending_episodes = await podcast_client.get_trending_episodes(max=100)
            # Convert episodes list to dict with ranks
            episodes_dict = {
                ep.id: idx + 1
                for idx, ep in enumerate(trending_episodes)
            }
        except Exception as e:
            logger.warning(f"Could not fetch trending episodes: {e}")

        # Store in cache with key "podcasts"
        # trending_podcasts is already a dict mapping feed_id to metadata
        db.set_trending_cache("podcasts", {
            "podcasts": trending_podcasts,
            "episodes": episodes_dict,
        })

        logger.info(
            f"Trending cache refreshed: {len(trending_podcasts)} podcasts, "
            f"{len(episodes_dict)} episodes"
        )

    except Exception as e:
        logger.error(f"Error refreshing trending cache: {e}", exc_info=True)


async def refresh_reddit_cache(db: Database):
    """Refresh Reddit mentions cache"""
    try:
        logger.info("Refreshing Reddit cache...")

        # Create RedditParser instance
        parser = RedditParser()

        # Parse all configured subreddits
        mentions = parser.parse_subreddits(REDDIT_SUBREDDITS, sort="hot")

        # Update database with mention counts
        for podcast_name, count in mentions.items():
            db.update_reddit_mention(podcast_name, REDDIT_SUBREDDITS, increment=count)

        logger.info(f"Reddit cache refreshed: {len(mentions)} podcasts mentioned")

    except Exception as e:
        logger.error(f"Error refreshing Reddit cache: {e}", exc_info=True)


async def background_cache_refresh_loop(db: Database, podcast_client: PodcastIndexClient):
    """Background loop that refreshes caches every 4 hours (2h trending + 2h Reddit)"""
    logger.info("Starting background cache refresh loop")

    try:
        while True:
            # Refresh trending cache
            await refresh_trending_cache(db, podcast_client)

            # Wait 2 hours
            await asyncio.sleep(2 * 60 * 60)

            # Refresh Reddit cache
            await refresh_reddit_cache(db)

            # Wait 2 hours (total 4 hour cycle)
            await asyncio.sleep(2 * 60 * 60)

    except asyncio.CancelledError:
        logger.info("Background cache refresh loop cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in background cache refresh loop: {e}", exc_info=True)
        # Retry with 60s delay
        await asyncio.sleep(60)
        # Re-raise to restart the loop
        raise
