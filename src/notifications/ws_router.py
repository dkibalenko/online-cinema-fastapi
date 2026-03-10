from fastapi import APIRouter, WebSocket

from notifications.websocket_manager import manager
from notifications.ws_auth import get_user_from_ws

router = APIRouter(prefix="/ws", tags=["notifications"])


@router.websocket("/comments")
async def comments_ws(websocket: WebSocket):
    """Establishes a WebSocket connection to receive comment notifications.

    The connection is authenticated using a JWT token passed as
    a query parameter.
    Once connected, the user will receive real-time notifications for new
    comments on movies they have previously commented on.

    The connection is kept alive by periodically sending and receiving empty
    text messages.
    When the connection is closed (either by the user or due to an error),
    the user is disconnected from the comment notification system.

    :param websocket: The WebSocket connection to establish.
    :return: None
    """
    user = await get_user_from_ws(websocket)

    await manager.connect(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except Exception:
        manager.disconnect(user.id, websocket)
