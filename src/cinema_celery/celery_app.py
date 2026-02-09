from celery import Celery
from celery.schedules import crontab

from config import get_settings


settings = get_settings()


app = Celery(
    "cinema",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "cinema_celery.tasks.email_tasks",
        "cinema_celery.tasks.cleanup_tasks",
    ]
)

# Beat schedule: run cleanup once per week (Sunday midnight)
app.conf.beat_schedule = {
    "cleanup-expired-tokens-every-hour": {
        "task": "cinema_celery.tasks.cleanup_tasks.cleanup_expired_tokens",
        "schedule": crontab(day_of_week="sunday", hour=0, minute=0),
        # "schedule": 60,
    },
}
