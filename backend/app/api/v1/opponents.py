import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.opponent_service import OpponentService

router = APIRouter(prefix="/opponents", tags=["opponents"])


@router.get("/{opponent_id}")
async def get_opponent(opponent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Single query: VPIP, PFR, aggression, river stats, 4-tier classification,
    and dynamic jam/call adjustments — no hand-history scan, no solver call.
    """
    profile = await OpponentService(db).get_profile_with_tier(opponent_id)
    if profile is None:
        raise HTTPException(404, "Opponent not found")
    return profile
