"""
VernacularCast FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.database import create_db_and_tables
from app.api.routes import jobs as jobs_router
from app.api.routes import health as health_router
from app.ws_manager import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VernacularCast API starting up — creating DB tables")
    create_db_and_tables()
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
