"""
feed_parser.py — RSS feed fetching and normalization

Supports type: rss sources.
Future: type: scraper sources will be handled by separate modules in scrapers/.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import feedparser
import httpx
import yaml
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent / "sources.yaml"
REQUEST_TIMEOUT = 15  # seconds


def _load_sources() -> list[dict]:
    """Load source definitions from sources.yaml."""
    with open(SOURCES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def _normalize_date(raw: str | None) -> str:
    """Parse any date string into ISO-8601 format. Falls back to current UTC time."""
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = dateutil_parser.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _clean_summary(text: str | None, max_len: int = 300) -> str:
    """Strip HTML tags and truncate summary text."""
    if not text:
        return ""
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


async def _fetch_rss(source: dict) -> list[dict]:
    """Fetch and parse a single RSS/Atom feed."""
    url = source["url"]
    name = source["name"]
    category = source.get("category", "")
    fetched_at = datetime.now(timezone.utc).isoformat()

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "newsecurity/1.0 (+https://github.com/newsecurity)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            raw_content = response.content
    except Exception as exc:
        logger.warning(f"[{name}] HTTP fetch failed: {exc}")
        return []

    feed = feedparser.parse(raw_content)

    if feed.bozo and not feed.entries:
        logger.warning(f"[{name}] Feed parse error: {feed.bozo_exception}")
        return []

    items = []
    filter_keyword = source.get("filter_keyword", "").lower()

    for entry in feed.entries:
        item_url = entry.get("link") or entry.get("id") or ""
        if not item_url:
            continue

        title = entry.get("title", "(제목 없음)").strip()
        summary = _clean_summary(
            entry.get("summary") or entry.get("description") or ""
        )

        # Keyword filtering
        if filter_keyword:
            content_to_check = (title + " " + summary).lower()
            if filter_keyword not in content_to_check:
                continue

        raw_date = (
            entry.get("published")
            or entry.get("updated")
            or entry.get("created")
        )
        published_at = _normalize_date(raw_date)

        items.append(
            {
                "title": title,
                "url": item_url,
                "summary": summary,
                "published_at": published_at,
                "source_name": name,
                "category": category,
                "fetched_at": fetched_at,
            }
        )

    logger.info(f"[{name}] Fetched {len(items)} items")
    return items


async def fetch_all_feeds() -> list[dict]:
    """
    Fetch all configured sources concurrently.
    RSS sources are handled here; scraper sources are dispatched to their modules.
    """
    sources = _load_sources()
    tasks = []

    for source in sources:
        src_type = source.get("type", "rss")
        if src_type == "rss":
            tasks.append(_fetch_rss(source))
        elif src_type == "scraper":
            # Future: dynamically import scrapers/<scraper_module>.py
            module_name = source.get("scraper_module", "")
            logger.warning(
                f"[{source['name']}] Scraper type not yet implemented "
                f"(module: {module_name}). Skipping."
            )
        else:
            logger.warning(f"[{source['name']}] Unknown source type '{src_type}'. Skipping.")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[dict] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Feed fetch exception: {result}")
        elif isinstance(result, list):
            all_items.extend(result)

    logger.info(f"Total fetched across all feeds: {len(all_items)} items")
    return all_items
