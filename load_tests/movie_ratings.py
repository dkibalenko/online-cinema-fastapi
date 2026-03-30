import random

from locust import task, SequentialTaskSet

from load_tests.config import VERIFY_SSL


class RatingTasks(SequentialTaskSet):
    @task(3)
    def get_rating_summary(self):
        movie_id = 1
        self.client.get(
            f"/movies/{movie_id}/rating",
            verify=VERIFY_SSL,
            name="/movies/[id]/rating",
        )

    @task(1)
    def rate_movie(self):
        movie_id = 1
        rating = random.randint(1, 10)
        self.client.post(
            f"/movies/{movie_id}/rating",
            json={"rating": rating},
            verify=VERIFY_SSL,
            name="/movies/[id]/rating",
        )

    @task(1)
    def delete_rating(self):
        movie_id = 1
        self.client.delete(
            f"/movies/{movie_id}/rating",
            verify=VERIFY_SSL,
            name="/movies/[id]/rating",
        )
