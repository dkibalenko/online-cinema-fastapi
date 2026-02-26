from typing import Dict, List
from fastapi import WebSocket

from logger_config import get_logger
from notifications.interfaces import WebSocketConnectionManagerInterface


log = get_logger()


class ConnectionManager(WebSocketConnectionManagerInterface):
    def __init__(self):
        # user_id → list of WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        log.info(f"User {user_id} connected")
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        log.info(f"User {user_id} disconnected")
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        if user_id not in self.active_connections:
            log.warning(f"User {user_id} not connected")
            return
        log.info(f"Sending message to user ID: {user_id}")
        for ws in self.active_connections[user_id]:
            await ws.send_json(message)


manager = ConnectionManager()
