"""Celery task definitions for async background processing."""

from app.tasks.generate_image import generate_image_task
from app.tasks.optimize_prompt import optimize_prompt_task

__all__ = [
    "generate_image_task",
    "optimize_prompt_task",
]
