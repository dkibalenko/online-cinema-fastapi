from fastapi import APIRouter, WebSocket

from notifications.ws_auth import get_user_from_ws
from notifications.websocket_manager import manager


router = APIRouter(prefix="/ws", tags=["notifications"])


@router.websocket("/comments")
async def comments_ws(websocket: WebSocket):
    user = await get_user_from_ws(websocket)

    await manager.connect(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except Exception:
        manager.disconnect(user.id, websocket)
