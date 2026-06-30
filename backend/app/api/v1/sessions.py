import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import orm
from app.schemas.schemas import SessionCreate, SessionOut
from app.services.hand_service import HandService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(user_id: uuid.UUID, payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = orm.PokerSession(user_id=user_id, **payload.model_dump())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/{session_id}/hands")
async def list_hands(session_id: uuid.UUID, limit: int = Query(50, le=200), offset: int = 0,
                      db: AsyncSession = Depends(get_db)):
    hands = await HandService(db).list_hands_for_session(session_id, limit, offset)
    return [{"hand_id": h.hand_id, "hero_cards": h.hero_cards, "result_bb": h.result_bb,
             "pot_size": h.pot_size, "timestamp": h.timestamp} for h in hands]
