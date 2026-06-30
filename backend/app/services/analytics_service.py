import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import orm


class AnalyticsService:
    """
    Maps to `analytics_cache`. Never recomputes VPIP/PFR/winrate/leak reports
    on every dashboard load — values are written here by a background worker
    (Celery task) after each session import, then served straight from cache.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metric(self, user_id: uuid.UUID, metric_name: str) -> dict | None:
        result = await self.db.execute(
            select(orm.AnalyticsCache).where(
                orm.AnalyticsCache.user_id == user_id,
                orm.AnalyticsCache.metric_name == metric_name,
            )
        )
        row = result.scalars().first()
        return None if row is None else {
            "metric_name": row.metric_name,
            "metric_value": row.metric_value,
            "updated_at": row.updated_at,
        }

    async def upsert_metric(self, user_id: uuid.UUID, metric_name: str, value: dict[str, Any]) -> None:
        result = await self.db.execute(
            select(orm.AnalyticsCache).where(
                orm.AnalyticsCache.user_id == user_id,
                orm.AnalyticsCache.metric_name == metric_name,
            )
        )
        row = result.scalars().first()
        if row:
            row.metric_value = value
        else:
            self.db.add(orm.AnalyticsCache(user_id=user_id, metric_name=metric_name, metric_value=value))
        await self.db.commit()
