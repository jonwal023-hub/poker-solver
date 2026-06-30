"""
Core CFR / ReBeL solver engine.

NOTE: This module hosts the existing solver implementation (three-reach CFR +
range-vs-range equity engine) exactly as designed — it is intentionally kept
isolated and untouched here. Paste the full solver source into this file:
RangeVsRangeEquityEngine, RangeEquityResult, ThreeReachCFRNode,
FullReachCFRTrainer, CorrectedSolverBot, plus supporting types
(Card, Hand, HandRange, ActionType, Street, Position, CactusKevEvaluator,
TrueZobristHasher, TranspositionTable, PublicBeliefState, StrategyDistribution,
EquityFeatures, BoardTexture).

Why isolated:
  - swappable/upgradeable independently (bump SOLVER_VERSION in core/config.py)
  - zero FastAPI/SQLAlchemy imports -> stays unit-testable standalone
  - engine_adapter.py is the ONLY file that translates DB rows <-> these objects
"""

# --- Paste original solver code below this line, unmodified ---
