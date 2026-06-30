import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Enum, Float, ForeignKey, Integer,
    String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

PlayerPosition = Enum("BTN", "SB", "BB", "UTG", "MP", "HJ", "CO", name="player_position")
StreetType = Enum("PREFLOP", "FLOP", "TURN", "RIVER", name="street_type")
ActionType = Enum("FOLD", "CHECK", "CALL", "BET", "RAISE", "ALL_IN", name="action_type")


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    sessions: Mapped[list["PokerSession"]] = relationship(back_populates="user", cascade="all, delete")
    opponent_profiles: Mapped[list["OpponentProfile"]] = relationship(back_populates="user", cascade="all, delete")


class PokerSession(Base):
    __tablename__ = "sessions"
    session_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    session_name: Mapped[str] = mapped_column(String(255))
    stakes: Mapped[str] = mapped_column(String(20))
    site: Mapped[str | None] = mapped_column(String(50))
    total_hands: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")
    hands: Mapped[list["Hand"]] = relationship(back_populates="session", cascade="all, delete")


class Hand(Base):
    __tablename__ = "hands"
    hand_id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.session_id", ondelete="CASCADE"))
    hero_cards: Mapped[str] = mapped_column(String(6))
    board_cards: Mapped[str | None] = mapped_column(String(15))
    position: Mapped[str] = mapped_column(PlayerPosition)
    result_bb: Mapped[float] = mapped_column(Float, default=0.0)
    pot_size: Mapped[float] = mapped_column(Float)
    showdown: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())

    session: Mapped["PokerSession"] = relationship(back_populates="hands")
    actions: Mapped[list["HandAction"]] = relationship(back_populates="hand", cascade="all, delete",
                                                         order_by="HandAction.action_order")
    analyses: Mapped[list["SolverAnalysis"]] = relationship(back_populates="hand", cascade="all, delete")
    snapshots: Mapped[list["DecisionSnapshot"]] = relationship(back_populates="hand", cascade="all, delete")


class HandAction(Base):
    __tablename__ = "hand_actions"
    __table_args__ = (
        CheckConstraint(
            "(action IN ('BET','RAISE','ALL_IN') AND size_bb IS NOT NULL AND size_bb > 0) OR "
            "(action IN ('FOLD','CHECK','CALL') AND size_bb IS NULL)",
            name="chk_action_size",
        ),
    )
    action_id: Mapped[uuid.UUID] = uuid_pk()
    hand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hands.hand_id", ondelete="CASCADE"))
    street: Mapped[str] = mapped_column(StreetType)
    player: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(ActionType)
    size_bb: Mapped[float | None] = mapped_column(Float)
    action_order: Mapped[int] = mapped_column(Integer)

    hand: Mapped["Hand"] = relationship(back_populates="actions")


class SolverAnalysis(Base):
    __tablename__ = "solver_analysis"
    __table_args__ = (CheckConstraint("ev_loss >= 0", name="chk_positive_loss"),)

    analysis_id: Mapped[uuid.UUID] = uuid_pk()
    hand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hands.hand_id", ondelete="CASCADE"))
    street: Mapped[str] = mapped_column(StreetType)
    recommended_action: Mapped[str] = mapped_column(String(50))
    actual_action: Mapped[str] = mapped_column(String(50))
    ev_recommended: Mapped[float] = mapped_column(Float)
    ev_actual: Mapped[float] = mapped_column(Float)
    ev_loss: Mapped[float] = mapped_column(Float)
    solver_version: Mapped[str] = mapped_column(String(20), default="1.0.0")

    hand: Mapped["Hand"] = relationship(back_populates="analyses")


class DecisionSnapshot(Base):
    __tablename__ = "decision_snapshots"
    snapshot_id: Mapped[uuid.UUID] = uuid_pk()
    hand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hands.hand_id", ondelete="CASCADE"))
    street: Mapped[str] = mapped_column(StreetType)
    state_hash: Mapped[str] = mapped_column(String(64))
    pot_size: Mapped[float] = mapped_column(Float)
    spr: Mapped[float] = mapped_column(Float)
    board_texture: Mapped[str | None] = mapped_column(String(100))
    hero_features: Mapped[dict] = mapped_column(JSONB, default=dict)
    villain_features: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    hand: Mapped["Hand"] = relationship(back_populates="snapshots")


class OpponentProfile(Base):
    __tablename__ = "opponent_profiles"
    __table_args__ = (UniqueConstraint("user_id", "screen_name"),)

    opponent_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    screen_name: Mapped[str] = mapped_column(String(50))
    hands_seen: Mapped[int] = mapped_column(Integer, default=0)
    vpip: Mapped[float] = mapped_column(Float, default=0.0)
    pfr: Mapped[float] = mapped_column(Float, default=0.0)
    aggression: Mapped[float] = mapped_column(Float, default=0.0)
    river_bluff_freq: Mapped[float] = mapped_column(Float, default=0.0)
    fold_to_cbet: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="opponent_profiles")


class AnalyticsCache(Base):
    __tablename__ = "analytics_cache"
    __table_args__ = (UniqueConstraint("user_id", "metric_name"),)

    cache_id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String(100))
    metric_value: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
