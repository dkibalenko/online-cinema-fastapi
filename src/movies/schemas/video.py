from datetime import datetime

from pydantic import BaseModel, ConfigDict

from movies.models import VideoStatus


class VideoFileSchema(BaseModel):
    """Schema for a VideoFile record returned in API responses."""

    id: int
    movie_id: int
    status: VideoStatus
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoUploadResponseSchema(BaseModel):
    """Response returned immediately after a video upload is accepted."""

    message: str
    video: VideoFileSchema
