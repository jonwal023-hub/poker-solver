import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/{user_id}/{metric_name}")
async def get_metric(user_id: uuid.UUID, metric_name: str, db: AsyncSession = Depends(get_db)):
    metric = await AnalyticsService(db).get_metric(user_id, metric_name)
    if metric is None:
        raise HTTPException(404, "Metric not cached yet — trigger recompute via worker")
    return metric
