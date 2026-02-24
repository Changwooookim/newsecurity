"""
main.py — KorSecNews FastAPI application

Endpoints:
  GET  /              → Serve the frontend dashboard (static/index.html)
  GET  /api/news      → List news items (paginated)
  GET  /api/sources   → List configured sources
  POST /api/refresh   → Trigger an immediate feed refresh
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import init_db, get_news, get_total_count
from scheduler import start_scheduler, run_refresh_now

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent / "sources.yaml"
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, start scheduler with an immediate first run."""
    await init_db()
    start_scheduler()

    # Run first fetch immediately without blocking startup
    asyncio.create_task(run_refresh_now())
    logger.info("Initial feed fetch task created.")

    yield  # app is running

    # Shutdown
    from scheduler import scheduler
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down.")


app = FastAPI(
    title="KorSecNews",
    description="국내외 보안 뉴스 대시보드",
    version="0.1.0",
    lifespan=lifespan,
)

# Serve static files (CSS, JS assets if split later)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Frontend ─────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index)


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/api/news")
async def api_news(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Return paginated news items ordered by published_at DESC."""
    items = await get_news(limit=limit, offset=offset)
    total = await get_total_count()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@app.get("/api/sources")
async def api_sources():
    """Return the list of configured news sources."""
    with open(SOURCES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    sources = data.get("sources", [])
    return {"sources": sources}


@app.post("/api/refresh")
async def api_refresh():
    """Trigger an immediate feed refresh and return result stats."""
    result = await run_refresh_now()
    return result
