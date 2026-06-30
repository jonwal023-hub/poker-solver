import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import orm

# 4-tier opponent classification using PFR and big-raise (aggression) rates.
# Thresholds are illustrative defaults — tune against population data.
TIER_THRESHOLDS = {
    "NIT": {"pfr_max": 0.12, "aggression_max": 0.25},
    "TAG": {"pfr_max": 0.22, "aggression_max": 0.45},
    "LAG": {"pfr_max": 0.35, "aggression_max": 0.70},
    "MANIAC": {"pfr_max": 1.01, "aggression_max": 1.01},
}


def classify_opponent(pfr: float, aggression: float) -> str:
    for tier, bounds in TIER_THRESHOLDS.items():
        if pfr <= bounds["pfr_max"] and aggression <= bounds["aggression_max"]:
            return tier
    return "MANIAC"


def jam_call_strategy(tier: str) -> dict:
    """Dynamic jam/call frequency adjustment keyed off opponent tier."""
    return {
        "NIT": {"call_jam_widen": -0.10, "jam_bluff_freq": 0.05},
        "TAG": {"call_jam_widen": 0.00, "jam_bluff_freq": 0.12},
        "LAG": {"call_jam_widen": 0.08, "jam_bluff_freq": 0.20},
        "MANIAC": {"call_jam_widen": 0.18, "jam_bluff_freq": 0.05},
    }[tier]


class OpponentService:
    """Maps to `opponent_profiles`."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: uuid.UUID, screen_name: str) -> orm.OpponentProfile:
        result = await self.db.execute(
            select(orm.OpponentProfile).where(
                orm.OpponentProfile.user_id == user_id,
                orm.OpponentProfile.screen_name == screen_name,
            )
        )
        profile = result.scalars().first()
        if profile is None:
            profile = orm.OpponentProfile(user_id=user_id, screen_name=screen_name)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        return profile

    async def get_profile_with_tier(self, opponent_id: uuid.UUID) -> dict | None:
        profile = await self.db.get(orm.OpponentProfile, opponent_id)
        if profile is None:
            return None
        tier = classify_opponent(profile.pfr, profile.aggression)
        return {
            "opponent_id": profile.opponent_id,
            "screen_name": profile.screen_name,
            "hands_seen": profile.hands_seen,
            "vpip": profile.vpip,
            "pfr": profile.pfr,
            "aggression": profile.aggression,
            "river_bluff_freq": profile.river_bluff_freq,
            "fold_to_cbet": profile.fold_to_cbet,
            "tier": tier,
            "jam_call_strategy": jam_call_strategy(tier),
        }
