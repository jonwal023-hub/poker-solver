import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Street = Literal["PREFLOP", "FLOP", "TURN", "RIVER"]
Position = Literal["BTN", "SB", "BB", "UTG", "MP", "HJ", "CO"]
Action = Literal["FOLD", "CHECK", "CALL", "BET", "RAISE", "ALL_IN"]


# ---- Users / Sessions ----
class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserOut(BaseModel):
    user_id: uuid.UUID
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    session_name: str
    stakes: str
    site: str | None = None


class SessionOut(BaseModel):
    session_id: uuid.UUID
    session_name: str
    stakes: str
    site: str | None
    total_hands: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Hands ----
class HandActionIn(BaseModel):
    street: Street
    player: str
    action: Action
    size_bb: float | None = None
    action_order: int


class HandCreate(BaseModel):
    session_id: uuid.UUID
    hero_cards: str = Field(min_length=4, max_length=6)
    board_cards: str | None = Field(default=None, max_length=15)
    position: Position
    result_bb: float = 0.0
    pot_size: float
    showdown: bool = False
    actions: list[HandActionIn] = Field(default_factory=list)


class HandActionOut(BaseModel):
    street: Street
    player: str
    action: Action
    size_bb: float | None
    order: int


class SolverAnalysisOut(BaseModel):
    street: Street
    recommended: str
    actual: str
    ev_recommended: float
    ev_actual: float
    ev_loss: float
    solver_version: str


class DecisionSnapshotOut(BaseModel):
    street: Street
    state_hash: str
    spr: float
    board_texture: str | None
    hero_features: dict[str, Any]
    villain_features: dict[str, Any]


class HandReviewOut(BaseModel):
    """Maps 1:1 to the `hand_review` SQL view — single round trip."""
    hand_id: uuid.UUID
    hero_cards: str
    board_cards: str | None
    position: Position
    result_bb: float
    pot_size: float
    showdown: bool
    timestamp: datetime
    action_sequence: list[HandActionOut] | None
    analysis: list[SolverAnalysisOut] | None
    snapshots: list[DecisionSnapshotOut] | None


# ---- Opponents ----
class OpponentProfileOut(BaseModel):
    opponent_id: uuid.UUID
    screen_name: str
    hands_seen: int
    vpip: float
    pfr: float
    aggression: float
    river_bluff_freq: float
    fold_to_cbet: float
    updated_at: datetime

    class Config:
        from_attributes = True


# ---- Analytics ----
class AnalyticsMetricOut(BaseModel):
    metric_name: str
    metric_value: dict[str, Any]
    updated_at: datetime
