import asyncio
import pathlib
import subprocess
import tempfile

import auth.models  # noqa: F401 — registers auth tokens in SQLAlchemy mapper registry
import users.models  # noqa: F401 — registers User in SQLAlchemy mapper registry

from cinema_celery.celery_app import app
from config import get_settings
from database import async_engine, get_db_contextmanager
from movies.models import VideoStatus
from movies.repositories.video import VideoFileRepository
from notifications.websocket_manager import manager
from storages.s3_client import S3StorageClient


def _get_s3_client() -> S3StorageClient:
    """Instantiate the S3 client from current settings."""
    settings = get_settings()
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME,
    )


@app.task
def transcode_to_hls(video_file_id: int) -> None:
    """Transcode a raw uploaded video to 360p and 720p HLS variants.

    Downloads the source file from MinIO, runs FFmpeg, uploads all HLS
    segments and playlists back to MinIO, then updates the VideoFile status.
    A WebSocket notification is sent to the uploader on completion or failure.

    Args:
        video_file_id (int): Primary key of the VideoFile record to process.
    """
    asyncio.run(_transcode(video_file_id))


async def _transcode(video_file_id: int) -> None:
    """Async implementation of the HLS transcode pipeline."""
    # Dispose stale pool connections from any previous event loop.
    # asyncio.run() creates a fresh loop each invocation; without dispose(),
    # asyncpg tries to reuse connections bound to the old loop and crashes.
    await async_engine.dispose()

    s3 = _get_s3_client()
    settings = get_settings()

    async with get_db_contextmanager() as db:
        repo = VideoFileRepository(db)
        video = await repo.get_by_id(video_file_id)

        if video is None:
            return

        await repo.update_status(video, VideoStatus.PROCESSING)
        movie_id = video.movie_id
        uploader_id = video.uploaded_by

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            source_path = tmp_path / "source.mp4"
            out_360 = tmp_path / "360p"
            out_720 = tmp_path / "720p"
            out_360.mkdir()
            out_720.mkdir()

            try:
                # 1. Download raw video from MinIO
                raw_bytes = await s3.download_file(video.raw_key)
                source_path.write_bytes(raw_bytes)

                # 2. Transcode 360p
                _run_ffmpeg(
                    input_path=str(source_path),
                    output_dir=str(out_360),
                    variant_name="360p",
                    scale="640:360",
                    video_bitrate="800k",
                )

                # 3. Transcode 720p
                _run_ffmpeg(
                    input_path=str(source_path),
                    output_dir=str(out_720),
                    variant_name="720p",
                    scale="1280:720",
                    video_bitrate="2800k",
                )

                # 4. Upload all HLS files to MinIO
                hls_base = f"videos/hls/{movie_id}"
                await _upload_directory(s3, out_360, f"{hls_base}/360p")
                await _upload_directory(s3, out_720, f"{hls_base}/720p")

                # 5. Build and upload master playlist
                base_url = (
                    f"{settings.S3_PUBLIC_ENDPOINT}"
                    f"/{settings.S3_BUCKET_NAME}/{hls_base}"
                )
                master = _build_master_playlist(base_url)
                await s3.upload_file(
                    f"{hls_base}/master.m3u8",
                    master.encode(),
                    content_type="application/x-mpegURL",
                )

                # 6. Mark ready
                await repo.update_status(video, VideoStatus.READY)

            except Exception as exc:
                await repo.update_status(
                    video, VideoStatus.FAILED, error=str(exc)
                )
                if uploader_id:
                    await manager.send_to_user(
                        uploader_id,
                        {
                            "type": "transcode_failed",
                            "movie_id": movie_id,
                            "error": str(exc),
                        },
                    )
                return

        # 7. Notify uploader
        if uploader_id:
            await manager.send_to_user(
                uploader_id,
                {
                    "type": "transcode_complete",
                    "movie_id": movie_id,
                    "stream_path": f"/api/v1/cinema/movies/{movie_id}/stream",
                },
            )


def _run_ffmpeg(
    input_path: str,
    output_dir: str,
    variant_name: str,
    scale: str,
    video_bitrate: str,
) -> None:
    """Run FFmpeg to produce an HLS variant in output_dir.

    Args:
        input_path (str): Path to the source video file.
        output_dir (str): Directory to write .m3u8 and .ts files into.
        variant_name (str): Used to name the playlist file (e.g. "360p").
        scale (str): FFmpeg scale filter value (e.g. "640:360").
        video_bitrate (str): Target video bitrate (e.g. "800k").
    """
    out = pathlib.Path(output_dir)
    playlist = str(out / f"{variant_name}.m3u8")
    segment_pattern = str(out / "seg%03d.ts")
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            input_path,
            "-vf",
            f"scale={scale}",
            "-c:v",
            "libx264",
            "-b:v",
            video_bitrate,
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-hls_time",
            "10",
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            segment_pattern,
            playlist,
        ],
        check=True,
        capture_output=True,
    )


async def _upload_directory(
    s3: S3StorageClient,
    local_dir: pathlib.Path,
    s3_prefix: str,
) -> None:
    """Upload every file in local_dir to MinIO under s3_prefix.

    Args:
        s3 (S3StorageClient): Configured S3 client.
        local_dir (pathlib.Path): Directory containing files to upload.
        s3_prefix (str): MinIO key prefix (e.g. "videos/hls/1/360p").
    """
    for file_path in sorted(local_dir.iterdir()):
        if not file_path.is_file():
            continue
        key = f"{s3_prefix}/{file_path.name}"
        content_type = (
            "application/x-mpegURL"
            if file_path.suffix == ".m3u8"
            else "video/MP2T"
        )
        await s3.upload_file(
            key, file_path.read_bytes(), content_type=content_type
        )


def _build_master_playlist(base_url: str) -> str:
    """Build the HLS master playlist content pointing to variant playlists.

    Args:
        base_url (str): Base URL where the HLS variant directories are hosted.

    Returns:
        str: The master .m3u8 playlist as a string.
    """
    return (
        "#EXTM3U\n"
        "#EXT-X-VERSION:3\n"
        f"#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360\n"
        f"{base_url}/360p/360p.m3u8\n"
        f"#EXT-X-STREAM-INF:BANDWIDTH=2800000,RESOLUTION=1280x720\n"
        f"{base_url}/720p/720p.m3u8\n"
    )
