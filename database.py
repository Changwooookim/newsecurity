"""
database.py — SQLite async database layer using aiosqlite
"""

import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "news.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS news_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    url          TEXT    NOT NULL UNIQUE,
    summary      TEXT,
    published_at TEXT,
    source_name  TEXT    NOT NULL,
    category     TEXT    NOT NULL DEFAULT '',
    fetched_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_published_at ON news_items (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_name  ON news_items (source_name);
"""


async def init_db() -> None:
    """Create the database and tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLE_SQL)
        await db.commit()
    logger.info(f"Database initialised at {DB_PATH}")


async def upsert_news_items(items: list[dict]) -> int:
    """
    Insert new news items, silently ignoring duplicates (same URL).
    Returns the number of newly inserted rows.
    """
    if not items:
        return 0

    async with aiosqlite.connect(DB_PATH) as db:
        # Get count before insertion
        async with db.execute("SELECT COUNT(*) FROM news_items") as cur:
            row = await cur.fetchone()
            count_before = row[0] if row else 0

        for item in items:
            try:
                await db.execute(
                    """
                    INSERT INTO news_items
                        (title, url, summary, published_at, source_name, category, fetched_at)
                    VALUES
                        (:title, :url, :summary, :published_at, :source_name, :category, :fetched_at)
                    ON CONFLICT(url) DO UPDATE SET
                        summary = CASE WHEN excluded.summary != '' THEN excluded.summary ELSE news_items.summary END,
                        fetched_at = excluded.fetched_at
                    """,
                    item,
                )
            except Exception as exc:
                logger.error(f"DB insert error for {item.get('url')}: {exc}")
        
        await db.commit()

        # Get count after insertion
        async with db.execute("SELECT COUNT(*) FROM news_items") as cur:
            row = await cur.fetchone()
            count_after = row[0] if row else 0

    return count_after - count_before


async def get_news(limit: int = 200, offset: int = 0) -> list[dict]:
    """Return news items ordered by published_at DESC."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, title, url, summary, published_at, source_name, category, fetched_at
            FROM   news_items
            ORDER  BY published_at DESC, fetched_at DESC
            LIMIT  ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_total_count() -> int:
    """Return the total number of stored news items."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM news_items") as cur:
            row = await cur.fetchone()
    return row[0] if row else 0
