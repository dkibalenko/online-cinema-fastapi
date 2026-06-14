import pathlib
import tempfile
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user, require_role
from cinema_celery.tasks.transcode_tasks import transcode_to_hls
from config import get_settings
from database import get_db
from movies.models import VideoFile, VideoStatus
from movies.repositories.video import VideoFileRepository
from movies.schemas.video import VideoFileSchema, VideoUploadResponseSchema
from storages.dependencies import get_s3_storage_client
from storages.interfaces import S3StorageInterface
from users.enums import UserGroupEnum
from users.models import User

router = APIRouter(prefix="/movies", tags=["Video Streaming"])

_ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


# --- static routes first ---


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
    db: Annotated[AsyncSession, Depends(get_db)],
    s3: Annotated[S3StorageInterface, Depends(get_s3_storage_client)],
    _: Annotated[
        User,
        Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN)),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> VideoUploadResponseSchema:
    """Upload a raw video file for a movie and queue HLS transcoding.

    Args:
        movie_id (int): ID of the movie to attach the video to.
        file (UploadFile): The raw video file.
        db (AsyncSession): Database session.
        s3 (S3StorageInterface): S3 storage client.
        current_user (User): The authenticated uploader.
    """
    suffix = pathlib.Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
            ),
        )

    repo = VideoFileRepository(db)
    existing = await repo.get_by_movie_id(movie_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A video already exists for this movie.",
        )

    # Stream UploadFile to a temp file to avoid loading large video into RAM
    raw_key = f"videos/raw/{movie_id}/original{suffix}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)
        chunk_size = 1024 * 1024  # 1 MB
        while chunk := await file.read(chunk_size):
            tmp.write(chunk)

    await s3.upload_file(
        raw_key,
        tmp_path.read_bytes(),
        content_type=file.content_type or "application/octet-stream",
    )
    tmp_path.unlink(missing_ok=True)

    video = VideoFile(
        movie_id=movie_id,
        raw_key=raw_key,
        status=VideoStatus.PENDING,
        uploaded_by=current_user.id,
    )
    repo.add(video)
    await repo.commit()
    await repo.refresh(video)

    transcode_to_hls.delay(video.id)

    return VideoUploadResponseSchema(
        message="Video upload accepted. Transcoding started.",
        video=VideoFileSchema.model_validate(video),
    )


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
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> VideoFileSchema:
    """Return the current transcode status for a movie's video.

    Args:
        movie_id (int): ID of the movie.
        db (AsyncSession): Database session.
    """
    repo = VideoFileRepository(db)
    video = await repo.get_by_movie_id(movie_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No video found for this movie.",
        )
    return VideoFileSchema.model_validate(video)


# --- dynamic routes below ---


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
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> RedirectResponse:
    """Redirect to the HLS master playlist for authenticated playback.

    Args:
        movie_id (int): ID of the movie to stream.
        db (AsyncSession): Database session.
    """
    repo = VideoFileRepository(db)
    video = await repo.get_by_movie_id(movie_id)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No video found for this movie.",
        )
    if video.status != VideoStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Video is not ready for streaming "
                f"(status: {video.status.value})."
            ),
        )

    settings = get_settings()
    manifest_url = (
        f"{settings.S3_STORAGE_ENDPOINT}"
        f"/{settings.S3_BUCKET_NAME}"
        f"/videos/hls/{movie_id}/master.m3u8"
    )
    return RedirectResponse(url=manifest_url, status_code=302)
