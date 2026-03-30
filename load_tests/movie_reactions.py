from locust import task, SequentialTaskSet

from load_tests.config import VERIFY_SSL


class ReactionTasks(SequentialTaskSet):
    @task(3)
    def get_reaction_summary(self):
        movie_id = 1
        self.client.get(
            f"/movies/{movie_id}/reactions",
            verify=VERIFY_SSL,
            name="/movies/[id]/reactions",
        )

    @task(1)
    def like_movie(self):
        movie_id = 1
        self.client.post(
            f"/movies/{movie_id}/like",
            verify=VERIFY_SSL,
            name="/movies/[id]/like",
        )

    @task(1)
    def dislike_movie(self):
        movie_id = 1
        self.client.post(
            f"/movies/{movie_id}/dislike",
            verify=VERIFY_SSL,
            name="/movies/[id]/dislike",
        )

    @task(1)
    def remove_reaction(self):
        movie_id = 1
        self.client.delete(
            f"/movies/{movie_id}/reaction-remove",
            verify=VERIFY_SSL,
            name="/movies/[id]/reaction-remove",
        )
