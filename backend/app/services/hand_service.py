import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import orm
from app.schemas.schemas import HandCreate


class HandService:
    """Maps to the `hands` + `hand_actions` tables."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_hand(self, data: HandCreate) -> orm.Hand:
        hand = orm.Hand(
            session_id=data.session_id,
            hero_cards=data.hero_cards,
            board_cards=data.board_cards,
            position=data.position,
            result_bb=data.result_bb,
            pot_size=data.pot_size,
            showdown=data.showdown,
        )
        self.db.add(hand)
        await self.db.flush()  # get hand_id

        for a in data.actions:
            self.db.add(orm.HandAction(
                hand_id=hand.hand_id, street=a.street, player=a.player,
                action=a.action, size_bb=a.size_bb, action_order=a.action_order,
            ))

        await self.db.commit()
        await self.db.refresh(hand)
        return hand

    async def get_hand_review(self, hand_id: uuid.UUID) -> dict | None:
        """
        Single round trip via the `hand_review` SQL view — this is the whole
        point of the schema: the frontend never reruns the solver on read.
        """
        result = await self.db.execute(
            text("SELECT * FROM hand_review WHERE hand_id = :hand_id"),
            {"hand_id": str(hand_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def list_hands_for_session(self, session_id: uuid.UUID, limit: int = 50, offset: int = 0):
        result = await self.db.execute(
            select(orm.Hand)
            .where(orm.Hand.session_id == session_id)
            .order_by(orm.Hand.timestamp.desc())
            .limit(limit).offset(offset)
        )
        return result.scalars().all()
