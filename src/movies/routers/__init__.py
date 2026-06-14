from movies.routers.crud import router as crud_router
from movies.routers.genres import router as genres_router
from movies.routers.interactions import router as interactions_router
from movies.routers.video import router as video_router

__all__ = [
    "crud_router",
    "genres_router",
    "interactions_router",
    "video_router",
]
