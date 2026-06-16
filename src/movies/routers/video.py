from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import RedirectResponse

from auth.dependencies import get_current_user, require_role
from movies.dependencies import get_video_service
from movies.schemas.video import VideoFileSchema, VideoUploadResponseSchema
from movies.services import VideoService
from users.enums import UserGroupEnum
from users.models import User

router = APIRouter(prefix="/movies", tags=["Video Streaming"])


@router.post(
    "/{movie_id}/video",
    response_model=VideoUploadResponseSchema,
    summary="Upload a video for a movie",
    description=(
        "Upload a raw video file for a movie and queue HLS transcoding. "
        "Only Moderators and Admins may upload. Returns immediately with "
        "status 'pending'; use the status endpoint to track progress."
    ),
    responses={
        202: {"description": "Video accepted and queued for transcoding"},
        400: {"description": "Unsupported file extension"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - insufficient permissions"},
        409: {"description": "A video already exists for this movie"},
    },
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_movie_video(
    movie_id: int,
    file: UploadFile,
    service: Annotated[VideoService, Depends(get_video_service)],
    _: Annotated[
        User,
        Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN)),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VideoUploadResponseSchema:
    """Upload a raw video file and queue HLS transcoding."""
    return await service.upload_video(movie_id, file, current_user.id)


@router.get(
    "/{movie_id}/video/status",
    response_model=VideoFileSchema,
    summary="Get video transcode status",
    description="Return the current transcode status for a movie's video.",
    responses={
        200: {"description": "Status returned successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "No video found for this movie"},
    },
    status_code=status.HTTP_200_OK,
)
async def get_video_status(
    movie_id: int,
    service: Annotated[VideoService, Depends(get_video_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> VideoFileSchema:
    """Return the current transcode status for a movie's video."""
    return await service.get_status(movie_id)


@router.get(
    "/{movie_id}/stream",
    summary="Stream a movie (HLS)",
    description=(
        "Redirect to the HLS master playlist for authenticated playback. "
        "Follow the 302 redirect with an HLS-capable player (e.g. hls.js)."
    ),
    responses={
        302: {"description": "Redirect to MinIO HLS master playlist"},
        401: {"description": "Unauthorized"},
        404: {"description": "No video found for this movie"},
        409: {"description": "Video not ready — transcoding in progress"},
    },
    status_code=status.HTTP_302_FOUND,
)
async def stream_movie(
    movie_id: int,
    service: Annotated[VideoService, Depends(get_video_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> RedirectResponse:
    """Redirect to the HLS master playlist for authenticated playback."""
    url = await service.get_stream_url(movie_id)
    return RedirectResponse(url=url, status_code=302)
