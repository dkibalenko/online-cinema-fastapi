import aioboto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError,
    HTTPClientError,
    NoCredentialsError,
)

from storages.exceptions import S3ConnectionError, S3FileUploadError
from storages.interfaces import S3StorageInterface


class S3StorageClient(S3StorageInterface):
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
    ):
        """Initialize the asynchronous S3 Storage Client.

        This client uses an aioboto3 Session.

        Args:
            endpoint_url (str): S3-compatible storage endpoint.
            access_key (str): Access key for authentication.
            secret_key (str): Secret key for authentication.
            bucket_name (str): Name of the bucket where files will be stored.
        """
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket_name = bucket_name

        self._session = aioboto3.Session(
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    async def upload_file(
        self,
        file_name: str,
        file_data: bytes | bytearray,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Asynchronously upload a file to the S3-compatible storage.

        Args:
            file_name (str): The name of the file to be stored.
            file_data (Union[bytes, bytearray]): The file data in bytes.
            content_type (str): MIME type of the file being uploaded.

        Raises:
            S3ConnectionError: If there is a connection error with S3.
            S3FileUploadError: If the file upload fails due to BotoCore error.
        """
        try:
            async with self._session.client(
                "s3", endpoint_url=self._endpoint_url
            ) as client:
                await client.put_object(
                    Bucket=self._bucket_name,
                    Key=file_name,
                    Body=file_data,
                    ContentType=content_type,
                )
        except (ConnectionError, HTTPClientError, NoCredentialsError) as e:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage: {str(e)}"
            ) from e
        except BotoCoreError as e:
            raise S3FileUploadError(
                f"Failed to upload to S3 storage: {str(e)}"
            ) from e

    async def download_file(self, file_name: str) -> bytes:
        """Download a file from S3-compatible storage and return its bytes.

        Args:
            file_name (str): The key of the file to download.

        Returns:
            bytes: Raw file contents.

        Raises:
            S3ConnectionError: If there is a connection error with S3.
            S3FileUploadError: If the download fails due to a BotoCore error.
        """
        try:
            async with self._session.client(
                "s3", endpoint_url=self._endpoint_url
            ) as client:
                response = await client.get_object(
                    Bucket=self._bucket_name, Key=file_name
                )
                return await response["Body"].read()
        except (ConnectionError, HTTPClientError, NoCredentialsError) as e:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage: {str(e)}"
            ) from e
        except (BotoCoreError, ClientError) as e:
            raise S3FileUploadError(
                f"Failed to download file from S3 storage: {str(e)}"
            ) from e

    async def get_file_url(self, file_name: str) -> str:
        """Generate public URL for a file stored in the S3-compatible storage.

        Args:
            file_name (str): The name of the file stored in the bucket.

        Returns:
            str: The full URL to access the file.
        """
        return f"{self._endpoint_url}/{self._bucket_name}/{file_name}"

    async def delete_file(self, file_name: str) -> None:
        """Delete a file from the S3-compatible storage.

        Args:
            file_name (str): The key of the file to delete.

        Raises:
            S3ConnectionError: If there is a connection issue.
            S3FileUploadError: If deletion fails due to S3 errors.
        """
        try:
            async with self._session.client(
                "s3", endpoint_url=self._endpoint_url
            ) as client:
                await client.delete_object(
                    Bucket=self._bucket_name, Key=file_name
                )

        except (ConnectionError, HTTPClientError, NoCredentialsError) as e:
            raise S3ConnectionError(
                f"Failed to connect to S3 storage: {str(e)}"
            ) from e

        except (BotoCoreError, ClientError) as e:
            raise S3FileUploadError(
                f"Failed to delete file from S3 storage: {str(e)}"
            ) from e
