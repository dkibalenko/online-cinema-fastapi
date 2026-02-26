from fastapi import WebSocket

from config import get_settings
from database import get_db_contextmanager
from logger_config import get_logger
from auth.interfaces import JWTAuthManagerInterface
from auth.token_manager import JWTAuthManager
from users.models import User
from users.repository import UserRepository


log = get_logger()


def get_jwt_manager() -> JWTAuthManagerInterface:
    """
    Retrieves an instance of the `JWTAuthManager` class based on
    the application settings.

    Returns:
        `JWTAuthManager`: An instance of the `JWTAuthManager` class.
    """
    settings = get_settings()
    return JWTAuthManager(
        secret_key_access=settings.JWT_SECRET_KEY_ACCESS.get_secret_value(),
        secret_key_refresh=settings.JWT_SECRET_KEY_REFRESH.get_secret_value(),
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


async def get_user_from_ws(websocket: WebSocket) -> User:
    """
    Retrieves a user from the given WebSocket connection.

    The user is identified by the "token" query parameter,
    which is used to authenticate the user.

    If the token is invalid or missing, the WebSocket connection is closed
    and an HTTPException is raised.

    If the user is not found, the WebSocket connection is closed and
    an HTTPException is raised.

    :param websocket: The WebSocket connection to authenticate.
    :return: The authenticated user.
    :raises HTTPException: If the token is invalid or missing,
        or if the user is not found.
    """
    # JWT‑authenticated WebSocket
    jwt_manager = get_jwt_manager()
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt_manager.decode_access_token(token)
    except Exception as e:
        log.warning(f"Invalid WS token: {token[:10]}... - {str(e)}")
        await websocket.close(code=1008)
        return

    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=1008)
        return

    async with get_db_contextmanager() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)

    if not user:
        await websocket.close(code=1008)
        return

    return user
