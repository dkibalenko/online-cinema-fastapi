from fastapi import HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from cinema_celery.tasks.comment_tasks import send_comment_reply_notification
from logger_config import get_logger
from movies.repositories import MovieRepository
from movies.schemas import CommentCreateSchema, CommentSchema
from notifications.websocket_manager import manager

log = get_logger()


class MovieCommentService:
    def __init__(self, repo: MovieRepository):
        self.repo = repo

    async def add_comment(
        self, movie_id: int, user_id: int, payload: CommentCreateSchema
    ) -> CommentSchema:
        """Add a comment to a movie.

        :param movie_id: The ID of the movie.
        :param user_id: The ID of the user.
        :param payload: The comment data.
        :return: The created comment object.
        :raises HTTPException:
            - `404 Not Found` if the movie does not exist
            - `400 Bad Request` if the parent comment does not exist or does
                not belong to the same movie
        """
        log.info(f"Adding comment | movie_id={movie_id} user_id={user_id}")

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for comment | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        parent = None
        if payload.parent_id:
            parent = await self.repo.get_comment_by_id(payload.parent_id)
            if not parent or parent.movie_id != movie_id:
                log.warning(
                    f"Invalid parent comment | parent_id={payload.parent_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid parent comment. Parent comment does not exist"
                        " or does not belong to the same movie."
                    ),
                )

        comment = await self.repo.create_comment(
            movie_id=movie_id,
            user_id=user_id,
            content=payload.content,
            parent_id=payload.parent_id,
        )

        await self.repo.commit()

        if parent:
            send_comment_reply_notification.delay(
                email=parent.user.email,
                movie_title=movie.name,
                reply_content=payload.content,
            )
            await manager.send_to_user(
                parent.user_id,
                {
                    "type": "comment_reply",
                    "movie_id": movie_id,
                    "comment_id": comment.id,
                    "content": payload.content,
                    "parent_id": payload.parent_id,
                    "created_at": comment.created_at.isoformat(),
                },
            )

        return CommentSchema.model_validate(comment)

    async def list_comments(self, movie_id: int) -> Page[CommentSchema]:
        """List comments for a specific movie.

        Args:
            movie_id (int): ID of the movie to list comments for.

        Returns:
            Page[CommentSchema]: A paginated list of comments for the movie.

        Raises:
            HTTPException: If the movie is not found.
        """
        log.info(f"Listing comments | movie_id={movie_id}")

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for comment | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        stmt = self.repo.get_comments_query(movie_id)
        return await paginate(self.repo.db, stmt)
