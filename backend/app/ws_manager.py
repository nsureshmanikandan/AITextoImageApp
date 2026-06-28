"""
Simple WebSocket connection manager for per-job progress streaming.
"""

import json
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, job_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[job_id].append(websocket)
        logger.info("WS connected for job %d (total: %d)", job_id, len(self.active[job_id]))

    def disconnect(self, job_id: int, websocket: WebSocket) -> None:
        if websocket in self.active[job_id]:
            self.active[job_id].remove(websocket)

    async def broadcast(self, job_id: int, data: dict) -> None:
        dead = []
        for ws in self.active.get(job_id, []):
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning("WS send failed for job %d: %s", job_id, e)
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)


ws_manager = ConnectionManager()
