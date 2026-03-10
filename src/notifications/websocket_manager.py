from fastapi import WebSocket

from logger_config import get_logger
from notifications.interfaces import WebSocketConnectionManagerInterface

log = get_logger()


class ConnectionManager(WebSocketConnectionManagerInterface):
    def __init__(self):
        # user_id → list of WebSocket connections
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        """Connects a user to a WebSocket connection.

        Logs a message with the user's ID on connection.

        Args:
            user_id (int): The user's ID.
            websocket (WebSocket): The WebSocket connection.
        """
        log.info(f"User {user_id} connected")
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        """Disconnects a user from the WebSocket connection.

        Args:
            user_id (int): The user's ID.
            websocket (WebSocket): The WebSocket connection.

        Logs a warning if the user is not connected.
        """
        log.info(f"User {user_id} disconnected")
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        """Sends a message to a user.

        If the user is not connected, a warning is logged.

        Args:
            user_id (int): The ID of the user to send the message to.
            message (dict): The message to send.

        Returns:
            None
        """
        if user_id not in self.active_connections:
            log.warning(f"User {user_id} not connected")
            return
        log.info(f"Sending message to user ID: {user_id}")
        for ws in self.active_connections[user_id]:
            await ws.send_json(message)


manager = ConnectionManager()
