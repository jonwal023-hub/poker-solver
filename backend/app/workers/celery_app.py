"""
Celery app for async, CPU-heavy work: solver runs and analytics recompute.
Keeps the FastAPI request thread free while CFR solves (which can take
seconds) run in the background; the frontend polls `GET /hands/{id}` until
`analysis` is populated.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("poker_solver", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.task_routes = {
    "app.workers.tasks.run_solver_analysis": {"queue": "solver"},
    "app.workers.tasks.recompute_analytics": {"queue": "analytics"},
}
