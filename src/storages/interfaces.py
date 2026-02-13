from abc import ABC, abstractmethod
from typing import Union


class S3StorageInterface(ABC):

    @abstractmethod
    async def upload_file(self, file_name: str, file_data: Union[bytes, bytearray]) -> None:
        """
        Asynchronously upload a file to the S3-compatible storage.

        Args:
            file_name (str): The name of the file to be stored.
            file_data (Union[bytes, bytearray]): The file data in bytes.
        """
        pass

    @abstractmethod
    async def get_file_url(self, file_name: str) -> str:
        """
        Generate a public URL for a file stored in the S3-compatible storage.

        :param file_name: The name of the file stored in the bucket.
        :return: The full URL to access the file.
        """
        pass
