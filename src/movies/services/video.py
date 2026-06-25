import pathlib
import tempfile

from fastapi import HTTPException, UploadFile, status

from cinema_celery.tasks.transcode_tasks import transcode_to_hls
from config import BaseAppSettings
from logger_config import get_logger
from movies.models import VideoFile, VideoStatus
from movies.repositories.video import VideoFileRepository
from movies.schemas.video import VideoFileSchema, VideoUploadResponseSchema
from storages.interfaces import S3StorageInterface

log = get_logger()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


class VideoService:
    def __init__(
        self,
        repo: VideoFileRepository,
        s3: S3StorageInterface,
        settings: BaseAppSettings,
    ):
        self.repo = repo
        self.s3 = s3
        self.settings = settings

    async def upload_video(
        self, movie_id: int, file: UploadFile, user_id: int
    ) -> VideoUploadResponseSchema:
        """Validate file, upload to MinIO, create VideoFile, queue transcode.

        :param movie_id: ID of the movie to attach the video to.
        :param file: The raw video upload.
        :param user_id: ID of the authenticated uploader.

        :raises HTTPException 400: Unsupported file extension.
        :raises HTTPException 409: A video already exists for this movie.

        :return: Upload confirmation with initial VideoFile state.
        """
        suffix = pathlib.Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported file type '{suffix}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
            )

        existing = await self.repo.get_by_movie_id(movie_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A video already exists for this movie.",
            )

        raw_key = f"videos/raw/{movie_id}/original{suffix}"

        # Stream to temp file - avoids loading GB-scale uploads into RAM
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            # build temp file path for later use
            tmp_path = pathlib.Path(tmp.name)
            chunk_size = 1024 * 1024  # 1 MB
            # read the upload in chunks and write to temp file
            while chunk := await file.read(chunk_size):
                tmp.write(chunk)  # takes bytes - UploadFile.read returns bytes

        # Upload temp file to MinIO and delete temp file after upload
        await self.s3.upload_file(
            raw_key,
            tmp_path.read_bytes(),  # file still exists on disk at tmp_path
            content_type=file.content_type or "application/octet-stream",
        )
        tmp_path.unlink(missing_ok=True)  # delete temp file after upload

        # Create VideoFile record in DB and queue transcode task
        video = VideoFile(
            movie_id=movie_id,
            raw_key=raw_key,
            status=VideoStatus.PENDING,
            uploaded_by=user_id,
        )
        self.repo.add(video)
        await self.repo.commit()
        await self.repo.refresh(video)

        # Queue the transcode task asynchronously using Celery
        transcode_to_hls.delay(video.id)

        log.info(
            f"Video upload accepted | movie_id={movie_id} video_id={video.id}"
        )

        return VideoUploadResponseSchema(
            message="Video upload accepted. Transcoding started.",
            video=VideoFileSchema.model_validate(video),
        )

    async def get_status(self, movie_id: int) -> VideoFileSchema:
        """Return the current transcode status for a movie's video.

        :param movie_id: ID of the movie.
        :raises HTTPException 404: No video found for this movie.
        :return: VideoFileSchema with current status.
        """
        video = await self.repo.get_by_movie_id(movie_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No video found for this movie.",
            )
        return VideoFileSchema.model_validate(video)

    async def get_stream_url(self, movie_id: int) -> str:
        """Return the MinIO master playlist URL for a ready video.

        :param movie_id: ID of the movie to stream.
        :raises HTTPException 404: No video found for this movie.
        :raises HTTPException 409: Video is not yet ready for streaming.
        :return: Absolute URL to the HLS master.m3u8 in MinIO.
        """
        video = await self.repo.get_by_movie_id(movie_id)
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

        return (
            f"{self.settings.S3_PUBLIC_ENDPOINT}"
            f"/{self.settings.S3_BUCKET_NAME}"
            f"/videos/hls/{movie_id}/master.m3u8"
        )
