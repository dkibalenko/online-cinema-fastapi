from abc import ABC, abstractmethod


class S3StorageInterface(ABC):
    @abstractmethod
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
        """
        pass

    @abstractmethod
    async def download_file(self, file_name: str) -> bytes:
        """Download a file from S3-compatible storage and return its bytes.

        Args:
            file_name (str): The key of the file to download.

        Returns:
            bytes: Raw file contents.
        """
        pass

    @abstractmethod
    async def get_file_url(self, file_name: str) -> str:
        """Generate public URL for a file stored in the S3-compatible storage.

        :param file_name: The name of the file stored in the bucket.
        :return: The full URL to access the file.
        """
        pass

    @abstractmethod
    async def delete_file(self, file_name: str) -> None:
        """Delete a file from S3-compatible storage."""
        pass
