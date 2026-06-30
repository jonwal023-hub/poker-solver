import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.schemas import HandCreate, HandReviewOut
from app.services.hand_service import HandService
from app.services.solver_service import SolverService

router = APIRouter(prefix="/hands", tags=["hands"])


@router.post("", status_code=201)
async def create_hand(payload: HandCreate, db: AsyncSession = Depends(get_db)):
    hand = await HandService(db).create_hand(payload)
    return {"hand_id": hand.hand_id}


@router.get("/{hand_id}", response_model=HandReviewOut)
async def get_hand_review(hand_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Single query via the `hand_review` view: hand + action_sequence +
    solver analysis + decision snapshots, all in one response. The solver
    is NEVER invoked here.
    """
    review = await HandService(db).get_hand_review(hand_id)
    if review is None:
        raise HTTPException(404, "Hand not found")
    return review


@router.post("/{hand_id}/analyze")
async def analyze_hand(hand_id: uuid.UUID, time_bank_seconds: float = 5.0,
                        db: AsyncSession = Depends(get_db)):
    """
    Explicitly trigger a solve for an unanalyzed hand (idempotent — guarded by
    the decision_snapshots.state_hash transposition check). This is the ONLY
    endpoint that runs the CFR engine.
    """
    try:
        results = await SolverService(db).analyze_hand(hand_id, time_bank_seconds)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"hand_id": hand_id, "streets_analyzed": len(results), "results": results}
