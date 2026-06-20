from typing import Annotated

from fastapi import Depends

from config import BaseAppSettings, get_settings
from storages.interfaces import S3StorageInterface
from storages.s3_client import S3StorageClient


async def get_s3_storage_client(
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
) -> S3StorageInterface:
    """Retrieve an instance of the S3StorageInterface.

    This function returns an instance of S3StorageClient configured with the
    application settings.

    This function instantiates an S3StorageClient using the provided settings,
    which include the S3 endpoint URL, access credentials, and the bucket name.
    The returned client can be used to interact with an S3-compatible storage
    service for file uploads and URL generation.

    Args:
        settings (BaseAppSettings, optional): The application settings,
        provided via dependency injection from `get_settings`.

    Returns:
        S3StorageInterface: An instance of S3StorageClient configured with the
        appropriate S3 storage settings.
    """
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME,
    )
