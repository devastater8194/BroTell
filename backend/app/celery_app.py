from celery import Celery
from app.config import settings

celery_app = Celery(
  "workspace_tasks",
  broker=settings.REDIS_URL,
  backend=settings.REDIS_URL,
  include=["app.tasks"]
)


celery_app.conf.update(
  task_serializer="json",
  accept_content=["json"],
  result_serializer="json",
  timezone="UTC",
  enable_utc=True,
  task_track_started=True,
  task_time_limit=600, # Max 10 minutes per task execution
  worker_prefetch_multiplier=1, # Fair dispatching of heavy tasks
)
