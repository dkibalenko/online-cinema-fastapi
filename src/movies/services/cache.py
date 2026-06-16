from cache.service import CacheService


class MovieCacheInvalidationService:
    def __init__(self, cache: CacheService):
        self.cache = cache

    async def invalidate_movie_lists(self, user_id: int | None = None):
        """Invalidate all movie lists for a user.

        If user_id is None, invalidate all movie lists.
        Otherwise, invalidate only the movie lists for the given user.

        Args:
            user_id (int | None): The ID of the user. If None, invalidate all
            movie lists.
        """
        if user_id:
            await self.cache.delete_pattern(f"movies:list:{user_id}:*")
        else:
            await self.cache.delete_pattern("movies:list:*")

    async def invalidate_reactions(self, movie_id: int, user_id: int):
        """Invalidate reaction summary for a user.

        Args:
            movie_id (int): The ID of the movie.
            user_id (int): The ID of the user.
        """
        await self.cache.delete(f"movie:{movie_id}:reactions:user:{user_id}")

    async def invalidate_rating(self, movie_id: int, user_id: int):
        """Invalidate the rating summary for a user.

        Args:
            movie_id (int): The ID of the movie.
            user_id (int): The ID of the user.

        Returns:
            None
        """
        await self.cache.delete(
            f"movie:{movie_id}:rating_summary:user:{user_id}"
        )
