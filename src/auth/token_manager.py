from datetime import UTC, datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt

from auth.interfaces import JWTAuthManagerInterface
from exceptions import InvalidTokenError, TokenExpiredError


class JWTAuthManager(JWTAuthManagerInterface):
    _ACCESS_KEY_EXPIRE_MINUTES = 15
    _REFRESH_KEY_EXPIRE_MINUTES = 60 * 24 * 7

    def __init__(
        self, secret_key_access: str, secret_key_refresh: str, algorithm: str
    ):
        self._secret_key_access = secret_key_access
        self._secret_key_refresh = secret_key_refresh
        self._algorithm = algorithm

    def _create_token(
        self, type: str, data: dict, secret_key: str, expires_delta: timedelta
    ) -> str:
        """Creates a new token.

        Uses the provided data, type, secret key, and expiration delta.
        The token will contain the provided data, the type of token
        (access or refresh), and an expiration time.
        The expiration time is calculated by adding the provided expiration
        delta to the current time in UTC.
        The token is encoded using the provided secret key and the configured
        algorithm.

        :param type: The type of token to create (access or refresh)
        :param data: The data to encode in the token
        :param secret_key: The secret key to use for encoding the token
        :param expires_delta: The expiration delta to use when calculating
            the expiration time
        :return: The created token as a string
        """
        to_encode = data.copy()
        expire = datetime.now(UTC) + expires_delta
        to_encode.update({"type": type, "exp": expire})
        return jwt.encode(to_encode, secret_key, algorithm=self._algorithm)

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """Creates a new access token using the provided data and secret key.

        Args:
            data (dict): Data to encode into the token.
            expires_delta (Optional[timedelta]): Time delta until the token
                expires.

        Returns:
            str: The newly created token.
        """
        return self._create_token(
            type="access",
            data=data,
            secret_key=self._secret_key_access,
            expires_delta=expires_delta
            or timedelta(minutes=self._ACCESS_KEY_EXPIRE_MINUTES),
        )

    def create_refresh_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """Creates a new refresh token using the provided data and secret key.

        Args:
            data (dict): Data to encode into the token.
            expires_delta (Optional[timedelta]): Time delta until the token
                expires.

        Returns:
            str: The newly created token.
        """
        return self._create_token(
            type="refresh",
            data=data,
            secret_key=self._secret_key_refresh,
            expires_delta=expires_delta
            or timedelta(minutes=self._REFRESH_KEY_EXPIRE_MINUTES),
        )

    def decode_access_token(self, token: str) -> dict:
        """Decodes an access token using the provided secret key."""
        try:
            return jwt.decode(
                token, self._secret_key_access, algorithms=[self._algorithm]
            )
        except ExpiredSignatureError as error:
            raise TokenExpiredError from error
        except JWTError as error:
            raise InvalidTokenError from error

    def decode_refresh_token(self, token: str) -> dict:
        """Decodes a refresh token using the provided secret key."""
        try:
            return jwt.decode(
                token, self._secret_key_refresh, algorithms=[self._algorithm]
            )
        except ExpiredSignatureError as error:
            raise TokenExpiredError from error
        except JWTError as error:
            raise InvalidTokenError from error

    def verify_refresh_token_or_raise(self, token: str) -> None:
        """Verify a refresh token or raise an error if invalid.

        Args:
            token (str): The refresh token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        self.decode_refresh_token(token)

    def verify_access_token_or_raise(self, token: str) -> None:
        """Verify an access token or raise an error if invalid.

        Args:
            token (str): The access token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        self.decode_access_token(token)
