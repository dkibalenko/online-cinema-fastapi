from locust import task, TaskSet

from load_tests.config import VERIFY_SSL


# def list_genres(user):  # Locust treats callables as tasks
#     user.client.get("/genres")


class GenreTasks(TaskSet):
    @task
    def list_genres(self):
        self.client.get("/genres", verify=VERIFY_SSL)
