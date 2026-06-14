from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from base_repository import BaseRepository
from movies.models import VideoFile, VideoStatus


class VideoFileRepository(BaseRepository):
    """Repository for VideoFile CRUD operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with an async DB session.

        Args:
            db (AsyncSession): The async SQLAlchemy session.
        """
        super().__init__(db)

    async def get_by_movie_id(self, movie_id: int) -> VideoFile | None:
        """Fetch the VideoFile record for the given movie, if one exists.

        Args:
            movie_id (int): Primary key of the Movie.

        Returns:
            VideoFile | None: The matching record or None.
        """
        result = await self.db.execute(
            select(VideoFile).where(VideoFile.movie_id == movie_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, video_id: int) -> VideoFile | None:
        """Fetch a VideoFile by its own primary key.

        Args:
            video_id (int): Primary key of the VideoFile.

        Returns:
            VideoFile | None: The matching record or None.
        """
        result = await self.db.execute(
            select(VideoFile).where(VideoFile.id == video_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        video: VideoFile,
        status: VideoStatus,
        error: str | None = None,
    ) -> None:
        """Set the transcode status (and optional error message) and commit.

        Args:
            video (VideoFile): The VideoFile instance to update.
            status (VideoStatus): New status to assign.
            error (str | None): Error message to store on failure.
        """
        video.status = status
        video.error_message = error
        await self.commit()
