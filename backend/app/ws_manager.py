"""
WebSocket connection managers:
- ConnectionManager: per-job progress streaming (existing)
- LiveNewsBroadcastManager: broadcast channel for live-news dashboard clients
"""

import json
import logging
from collections import defaultdict
from typing import Dict, List, Literal

from fastapi import WebSocket

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-job WebSocket manager (existing, unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Live-news broadcast channel for dashboard clients
# ---------------------------------------------------------------------------

# Valid message types for the live-news WebSocket channel
LiveNewsMessageType = Literal[
    "feed_status",
    "new_queue_item",
    "breaking_alert",
    "stats_update",
    "monitor_state",
]


class LiveNewsBroadcastManager:
    """Manages WebSocket connections for the /ws/live-news broadcast channel.

    All connected dashboard clients receive the same messages. Disconnected
    clients are removed gracefully during the next broadcast attempt.
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new dashboard WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "Live-news WS connected (total clients: %d)",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a client from the active connections list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "Live-news WS disconnected (total clients: %d)",
                len(self.active_connections),
            )

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected dashboard clients.

        Expected message format: {"type": <LiveNewsMessageType>, "payload": <dict>}
        Disconnected clients are cleaned up automatically.
        """
        dead: List[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning("Live-news WS send failed: %s", e)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# Singleton instance used throughout the application
live_news_ws = LiveNewsBroadcastManager()
