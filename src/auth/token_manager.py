from typing import Optional
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt, ExpiredSignatureError

from auth.interfaces import JWTAuthManagerInterface
from exceptions import TokenExpiredError, InvalidTokenError


class JWTAuthManager(JWTAuthManagerInterface):
    _ACCESS_KEY_EXPIRE_MINUTES = 15
    _REFRESH_KEY_EXPIRE_MINUTES = 60 * 24 * 7

    def __init__(
        self,
        secret_key_access: str,
        secret_key_refresh: str,
        algorithm: str
    ):
        """
        Initialize the manager with secret keys and algorithm for token operations.
        """
        self._secret_key_access = secret_key_access
        self._secret_key_refresh = secret_key_refresh
        self._algorithm = algorithm

    def _create_token(
        self,
        type: str,
        data: dict,
        secret_key: str,
        expires_delta: timedelta
    ) -> str:
        """
        Creates a new token using the provided data and secret key.
        
        Args:
            data (dict): Data to encode into the token.
            secret_key (str): Secret key to use for signing the token.
            expires_delta (timedelta): Time delta until the token expires.
        
        Returns:
            str: The newly created token.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"type": type, "exp": expire})
        return jwt.encode(to_encode, secret_key, algorithm=self._algorithm)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Creates a new access token using the provided data and secret key.

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
            expires_delta=expires_delta or timedelta(
                minutes=self._ACCESS_KEY_EXPIRE_MINUTES
                )
            )

    def create_refresh_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Creates a new refresh token using the provided data and secret key.

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
            expires_delta=expires_delta or timedelta(
                minutes=self._REFRESH_KEY_EXPIRE_MINUTES)
            )

    def decode_access_token(self, token: str) -> dict:
        """
        Decodes an access token using the provided secret key.
        """
        try:
            return jwt.decode(
                token,
                self._secret_key_access,
                algorithms=[self._algorithm]
            )
        except ExpiredSignatureError:
            raise TokenExpiredError
        except JWTError:
            raise InvalidTokenError

    def decode_refresh_token(self, token: str) -> dict:
        """
        Decodes a refresh token using the provided secret key.
        """
        try:
            return jwt.decode(
                token,
                self._secret_key_refresh,
                algorithms=[self._algorithm]
            )
        except ExpiredSignatureError:
            raise TokenExpiredError
        except JWTError:
            raise InvalidTokenError

    def verify_refresh_token_or_raise(self, token: str) -> None:
        """
        Verify a refresh token or raise an error if invalid.

        Args:
            token (str): The refresh token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        self.decode_refresh_token(token)

    def verify_access_token_or_raise(self, token: str) -> None:
        """
        Verify an access token or raise an error if invalid.

        Args:
            token (str): The access token to verify.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        self.decode_access_token(token)
