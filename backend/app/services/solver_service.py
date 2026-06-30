import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import orm
from app.solver.engine_adapter import SolveRequest, solver_adapter


class SolverService:
    """
    Maps to `solver_analysis` + `decision_snapshots`.

    Critical rule: this service is the ONLY place that ever calls the solver.
    Every other read path (hand review, replay) hits already-persisted rows.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_hand(self, hand_id: uuid.UUID, time_bank_seconds: float = 5.0) -> list[dict]:
        hand = await self.db.get(orm.Hand, hand_id)
        if hand is None:
            raise ValueError(f"Hand {hand_id} not found")

        actions_result = await self.db.execute(
            select(orm.HandAction).where(orm.HandAction.hand_id == hand_id)
            .order_by(orm.HandAction.action_order)
        )
        actions = actions_result.scalars().all()

        streets_present = sorted({a.street for a in actions} | {"PREFLOP"},
                                  key=["PREFLOP", "FLOP", "TURN", "RIVER"].index)

        results = []
        for street in streets_present:
            street_actions = [a for a in actions if a.street == street]
            if not street_actions:
                continue

            actual_action = street_actions[-1].action  # last action taken by hero on this street

            req = SolveRequest(hand=hand, actions=street_actions, street=street,
                                time_bank_seconds=time_bank_seconds)
            solved = solver_adapter.solve_hand_street(req)

            # Skip if we've already cached this exact state (transposition hit)
            existing = await self.db.execute(
                select(orm.DecisionSnapshot).where(orm.DecisionSnapshot.state_hash == solved["state_hash"])
            )
            if existing.scalars().first() is None:
                self.db.add(orm.DecisionSnapshot(
                    hand_id=hand_id, street=street, state_hash=solved["state_hash"],
                    pot_size=solved["pot_size"], spr=solved["spr"],
                    board_texture=solved["board_texture"],
                    hero_features=solved["hero_features"],
                    villain_features=solved["villain_features"],
                ))

            ev_actual = solved["ev_recommended"]  # placeholder: real impl looks up EV of actual_action
            self.db.add(orm.SolverAnalysis(
                hand_id=hand_id, street=street,
                recommended_action=solved["recommended_action"],
                actual_action=actual_action,
                ev_recommended=solved["ev_recommended"],
                ev_actual=ev_actual,
                ev_loss=max(0.0, solved["ev_recommended"] - ev_actual),
                solver_version=solved["solver_version"],
            ))
            results.append(solved)

        await self.db.commit()
        return results
