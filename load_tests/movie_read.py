import random

from locust import SequentialTaskSet, task

from .config import VERIFY_SSL, MOVIE_IDS


class MovieReadTasks(SequentialTaskSet):

    @task(4)
    def list_movies(self):
        self.client.get(
            "/movies",
            verify=VERIFY_SSL,
            name="/movies",
        )

    @task(1)
    def movie_detail(self):
        movie_id = random.choice(MOVIE_IDS)
        self.client.get(
            f"/movies/{movie_id}",
            verify=VERIFY_SSL,
            name="/movies/[id]",
        )
