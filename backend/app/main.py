"""
VernacularCast FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio

from app.database import create_db_and_tables
from app.api.routes import jobs as jobs_router
from app.api.routes import health as health_router
from app.ws_manager import ws_manager
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _recover_stuck_jobs() -> None:
    """On startup, mark any jobs stuck in mid-pipeline states as failed.
    These are jobs whose background task was killed by a server reload."""
    from sqlmodel import Session, select
    from app.database import engine
    from app.models.job import Job

    stuck_statuses = {"pending", "scraping", "generating_script", "generating_voice", "rendering_video"}
    with Session(engine) as session:
        jobs = session.exec(select(Job).where(Job.status.in_(stuck_statuses))).all()
        for job in jobs:
            logger.warning("Recovering stuck job %d (was: %s) → failed", job.id, job.status)
            job.status = "failed"
            job.error = f"Pipeline interrupted by server restart (was: {job.status})"
            job.append_step("pipeline", "failed", "Server restarted — please resubmit")
            session.add(job)
        if jobs:
            session.commit()
            logger.info("Recovered %d stuck job(s)", len(jobs))


def _run_db_migrations() -> None:
    """Apply incremental ALTER TABLE migrations for columns added after initial schema."""
    from app.database import engine as _engine
    with _engine.connect() as conn:
        for stmt in (
            "ALTER TABLE job ADD COLUMN mode TEXT NOT NULL DEFAULT 'article'",
            "ALTER TABLE job ADD COLUMN brand_data TEXT",
        ):
            try:
                conn.execute(__import__("sqlalchemy").text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VernacularCast API starting up — creating DB tables")
    create_db_and_tables()
    _run_db_migrations()
    _recover_stuck_jobs()
    yield
    logger.info("VernacularCast API shutting down")


app = FastAPI(
    title="VernacularCast API",
    description="AI video newsroom backend for regional Indian journalists",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins (hackathon setting; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router.router, prefix="/api")
app.include_router(jobs_router.router, prefix="/api")

# Serve rendered videos from the local media directory
_media_dir = Path(settings.local_media_dir).resolve()
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")


# WebSocket endpoint — registered directly on app (outside /jobs prefix)
@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: int):
    await ws_manager.connect(job_id, websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        ws_manager.disconnect(job_id, websocket)
    except Exception as e:
        logger.warning("WebSocket error for job %d: %s", job_id, e)
        ws_manager.disconnect(job_id, websocket)


@app.get("/", tags=["root"])
async def root():
    return {
        "service": "VernacularCast API",
        "docs": "/docs",
        "health": "/health",
    }
