import asyncio
import uuid

from app.db.session import AsyncSessionLocal
from app.services.solver_service import SolverService
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.run_solver_analysis")
def run_solver_analysis(hand_id: str, time_bank_seconds: float = 5.0):
    async def _run():
        async with AsyncSessionLocal() as db:
            return await SolverService(db).analyze_hand(uuid.UUID(hand_id), time_bank_seconds)
    return asyncio.run(_run())


@celery_app.task(name="app.workers.tasks.recompute_analytics")
def recompute_analytics(user_id: str):
    # Placeholder: aggregate hands -> VPIP/PFR/winrate/leak report -> AnalyticsService.upsert_metric
    return {"user_id": user_id, "status": "queued"}
