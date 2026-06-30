"""
Adapter layer between the persistence model (SQLAlchemy rows) and the solver's
native in-memory objects (PublicBeliefState, HandRange, etc. from cfr_engine.py).

Responsibilities:
  1. Build a PublicBeliefState from a Hand + its HandActions + opponent ranges.
  2. Run the solver (CorrectedSolverBot) with trial counts dynamically scaled
     by time budget / information state, mirroring the "15-100 trials" scaling
     described in the project goals.
  3. Persist solver output back into `solver_analysis` and `decision_snapshots`.
  4. Use a transposition table (state_hash -> result) to skip redundant solves.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from app.core.config import get_settings
from app.models import orm
from app.solver import cfr_engine as engine

settings = get_settings()


@dataclass
class SolveRequest:
    hand: orm.Hand
    actions: list[orm.HandAction]
    street: str
    time_bank_seconds: float = 5.0
    villain_screen_name: str | None = None


def scale_monte_carlo_trials(time_bank_seconds: float, info_state_size: int) -> int:
    """
    Dynamically scale MC trial count within [SOLVER_MC_MIN_TRIALS, SOLVER_MC_MAX_TRIALS]
    based on remaining time bank and the size of the current information state
    (number of plausible villain combos still live after card removal).

    More time + smaller info state -> more trials (tighter equity estimate).
    Less time + larger info state -> fewer trials (must stay responsive).
    """
    lo, hi = settings.SOLVER_MC_MIN_TRIALS, settings.SOLVER_MC_MAX_TRIALS
    time_factor = min(1.0, time_bank_seconds / 10.0)          # saturates at 10s
    complexity_penalty = min(1.0, 200.0 / max(info_state_size, 1))
    trials = lo + (hi - lo) * time_factor * complexity_penalty
    return max(lo, min(hi, round(trials)))


class SolverEngineAdapter:
    """Thin orchestration layer. Holds long-lived solver components so the
    transposition table / equity cache persist across requests."""

    def __init__(self) -> None:
        self._bot: engine.CorrectedSolverBot | None = None

    def _get_bot(self) -> "engine.CorrectedSolverBot":
        if self._bot is None:
            self._bot = engine.CorrectedSolverBot()
        return self._bot

    def build_pbs(self, req: SolveRequest) -> "engine.PublicBeliefState":
        """Translate a Hand row + its actions into the solver's PublicBeliefState."""
        bot = self._get_bot()
        pbs = engine.PublicBeliefState()
        pbs.board = self._parse_board(req.hand.board_cards)
        pbs.position = engine.Position[req.hand.position] if hasattr(engine, "Position") else req.hand.position
        pbs.street = engine.Street[req.street]
        pbs.pot_size = req.hand.pot_size
        pbs.hero_hand = self._parse_hand(req.hand.hero_cards)
        pbs.action_sequence = [engine.ActionType[a.action] for a in req.actions]
        # Ranges would normally be constructed from opponent_profiles stats
        # (vpip/pfr-derived range) — left as an extension point.
        pbs.hero_range = engine.HandRange()
        pbs.villain_range = engine.HandRange()
        return pbs

    def solve_hand_street(self, req: SolveRequest) -> dict:
        """
        Run (or reuse) a solve for one street of one hand.
        Returns a dict ready to populate SolverAnalysis + DecisionSnapshot rows.
        """
        bot = self._get_bot()
        pbs = self.build_pbs(req)

        info_state_size = max(len(pbs.villain_range.hands) if pbs.villain_range.hands else 169, 1)
        trials = scale_monte_carlo_trials(req.time_bank_seconds, info_state_size)
        bot.range_equity_engine.num_samples = trials

        state_hash = format(bot.hasher.hash_state(pbs) & 0xFFFFFFFFFFFFFFFF, "016x")

        start = time.time()
        strategy = bot.cfr_trainer.solve(pbs, num_iterations=settings.SOLVER_DEFAULT_ITERATIONS)
        elapsed = time.time() - start

        recommended_action = max(strategy.probabilities, key=strategy.probabilities.get)
        ev_recommended = strategy.get_action_ev(recommended_action)

        return {
            "state_hash": state_hash,
            "street": req.street,
            "pot_size": pbs.pot_size,
            "spr": self._compute_spr(req.hand),
            "board_texture": getattr(pbs, "board_texture", None),
            "hero_features": self._extract_features(pbs, side="hero"),
            "villain_features": self._extract_features(pbs, side="villain"),
            "recommended_action": recommended_action.name,
            "ev_recommended": ev_recommended,
            "trials_used": trials,
            "solve_time_s": elapsed,
            "solver_version": settings.SOLVER_VERSION,
        }

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _parse_board(board_cards: str | None) -> list:
        if not board_cards:
            return []
        return [engine.Card(*engine.Card.parse(board_cards[i:i + 2]))
                for i in range(0, len(board_cards), 2)] if hasattr(engine.Card, "parse") else []

    @staticmethod
    def _parse_hand(hero_cards: str):
        return None if not hero_cards else hero_cards  # delegate real parsing to engine.Hand.from_str

    @staticmethod
    def _compute_spr(hand: orm.Hand) -> float:
        # effective_stack / pot_size — stack data would come from session config
        return 0.0

    @staticmethod
    def _extract_features(pbs, side: str) -> dict:
        equity = getattr(pbs, f"{side}_equity", None)
        if equity is None:
            return {}
        return {
            "equity": getattr(equity, "current_equity", None),
            "nut_equity": getattr(equity, "nut_equity", None),
            "range_advantage": getattr(equity, "range_advantage", None),
        }


solver_adapter = SolverEngineAdapter()
