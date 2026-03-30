from locust import HttpUser, between, TaskSet

from load_tests.config import BASE_URL
from load_tests.auth_helpers import login_and_set_headers
from load_tests.movie_read import MovieReadTasks
from load_tests.genres import GenreTasks
from load_tests.movie_ratings import RatingTasks
from load_tests.movie_reactions import ReactionTasks


class RootTasks(TaskSet):
    tasks = {
        MovieReadTasks: 5,  # 5× more likely to be chosen (as weight)
        GenreTasks: 1,
        RatingTasks: 1,
        ReactionTasks: 1,
    }


class MovieUser(HttpUser):
    """
    Scenario:
    - on_start: login once, set auth + rate-limit-bypass header
    - then: mostly list movies, sometimes hit details
    """
    host = BASE_URL
    wait_time = between(1, 3)
    tasks = [RootTasks]

    def on_start(self):
        login_and_set_headers(self.client)


# 5 parts MovieRead -> 83% of the time → MovieRead
# 1 part GenreTasks -> 17% of the time → GenreTasks
