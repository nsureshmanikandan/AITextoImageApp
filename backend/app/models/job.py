from typing import Optional
from datetime import datetime
import json
from sqlmodel import SQLModel, Field


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default="pending")          # pending → scraping → generating_script → generating_voice → rendering_video → awaiting_review → approved → ready | failed
    steps_json: str = Field(default="[]")           # JSON list of {step, status, message, ts}
    error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    article_url: str
    language: str                                   # ta-IN | hi-IN | te-IN | kn-IN | en-IN
    format: str = Field(default="landscape_16_9")   # vertical_9_16 | landscape_16_9
    script: Optional[str] = Field(default=None)
    video_path: Optional[str] = Field(default=None)

    def append_step(self, step: str, status: str, message: str) -> None:
        steps = json.loads(self.steps_json)
        steps.append({
            "step": step,
            "status": status,
            "message": message,
            "ts": datetime.utcnow().isoformat(),
        })
        self.steps_json = json.dumps(steps)

    def get_steps(self) -> list:
        return json.loads(self.steps_json)


class JobCreate(SQLModel):
    article_url: str
    language: str = "en-IN"
    format: str = "landscape_16_9"


class JobRead(SQLModel):
    id: int
    status: str
    steps_json: str
    error: Optional[str]
    created_at: datetime
    article_url: str
    language: str
    format: str
    script: Optional[str]
    video_path: Optional[str]
