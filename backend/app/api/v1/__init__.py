"""API v1 package - combines all sub-routers into a single versioned router."""

from fastapi import APIRouter

from app.api.v1.generate import router as generate_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.history import router as history_router
from app.api.v1.regenerate import router as regenerate_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.images import router as images_router
from app.api.v1.presets import router as presets_router
from app.api.v1.health import router as health_router
from app.api.v1.overlays import router as overlays_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(generate_router)
api_router.include_router(jobs_router)
api_router.include_router(history_router)
api_router.include_router(regenerate_router)
api_router.include_router(prompts_router)
api_router.include_router(images_router)
api_router.include_router(presets_router)
api_router.include_router(health_router)
api_router.include_router(overlays_router)
