"""
scheduler.py — Background job scheduler (APScheduler)

Runs fetch_all_feeds() on startup and every hour thereafter.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from feed_parser import fetch_all_feeds
from database import upsert_news_items

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _refresh_job() -> None:
    """Fetch all feeds and store results in the database."""
    logger.info("Scheduler: starting feed refresh…")
    items = await fetch_all_feeds()
    count = await upsert_news_items(items)
    logger.info(f"Scheduler: refresh complete — {count} new items inserted.")


def start_scheduler() -> None:
    """Register the hourly job and start the scheduler."""
    scheduler.add_job(
        _refresh_job,
        trigger=IntervalTrigger(hours=1),
        id="hourly_refresh",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started (interval: 1 hour).")


async def run_refresh_now() -> dict:
    """Trigger an immediate feed refresh (called from API endpoint)."""
    items = await fetch_all_feeds()
    count = await upsert_news_items(items)
    return {"status": "ok", "new_items": count, "total_fetched": len(items)}
