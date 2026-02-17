class MovieBaseError(Exception):
    def __init__(self, message: str | None = None):
        if message is None:
            message = "A movie error occurred."
        super().__init__(message)


class MovieNotFoundError(MovieBaseError):
    """Raised when a movie is not found."""

    def __init__(self, message: str = "Movie not found."):
        super().__init__(message)
