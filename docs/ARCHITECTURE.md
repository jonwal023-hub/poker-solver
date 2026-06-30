# Architecture

## 1. System overview

```
┌─────────────┐      HTTPS/JSON       ┌──────────────────┐
│  React SPA   │ ───────────────────► │  FastAPI backend  │
│ (Vite, TS)   │ ◄─────────────────── │  /api/v1/*         │
└─────────────┘                       └─────────┬──────────┘
                                                 │
                         ┌───────────────────────┼───────────────────────┐
                         ▼                       ▼                       ▼
                 ┌───────────────┐     ┌──────────────────┐    ┌──────────────────┐
                 │  PostgreSQL    │     │  Redis (cache +   │    │  Celery worker(s) │
                 │  (schema v2.0) │     │  Celery broker)   │    │  -> CFR solver     │
                 └───────────────┘     └──────────────────┘    └──────────────────┘
```

The FastAPI app is a thin, mostly-CRUD layer. The only CPU-heavy path is
`POST /hands/{id}/analyze`, which enqueues a Celery task that calls the
solver (`app/solver/engine_adapter.py` → `app/solver/cfr_engine.py`) and
writes results back into `solver_analysis` + `decision_snapshots`. Every
other read (`GET /hands/{id}`, `GET /opponents/{id}`, `GET /analytics/...`)
is a single indexed SQL query against already-materialized data.

## 2. Why this shape

The project's own design doc (the "Final Database Architecture" notes)
makes the key architectural decision: **store the solver's *outputs* and
*compressed inputs*, never its full internal state.**

- `hands` stays a tiny, denormalized table (`hero_cards`, `board_cards` as
  raw strings) — no card-combination join tables.
- `hand_actions` is an append-only, ordered log — sufficient to fully
  reconstruct and replay a hand without any state machine in the DB.
- `solver_analysis` is a precomputed diff between the GTO-recommended line
  and what the player actually did (`ev_loss`), so hand review is instant.
- `decision_snapshots` stores the **compressed Public Belief State**
  (nut density, draw density, blocker strength, equity, `state_hash`) —
  never the full 1326-combo range distribution. This is the ReBeL-style
  state representation, kept small enough to index and query with GIN.
- `opponent_profiles` stores precomputed VPIP/PFR/aggression/river stats —
  no hand-history scan at request time.
- `analytics_cache` stores dashboard-ready JSON blobs keyed by
  `(user_id, metric_name)`, refreshed by a background worker.

## 3. Solver integration contract

`app/solver/cfr_engine.py` is treated as a black box (per the existing
implementation: `RangeVsRangeEquityEngine`, `ThreeReachCFRNode`,
`FullReachCFRTrainer`, `CorrectedSolverBot`). `engine_adapter.py` is the
**only** file allowed to import it, and is responsible for:

1. Building a `PublicBeliefState` from `Hand` + `HandAction` rows.
2. Dynamically scaling Monte Carlo trial count
   (`SOLVER_MC_MIN_TRIALS`–`SOLVER_MC_MAX_TRIALS`, default 15–100) based on
   time bank and information-state size (`scale_monte_carlo_trials`).
3. Checking `decision_snapshots.state_hash` before solving — if the exact
   PBS state was already solved (transposition table hit), skip the solve.
4. Returning a plain dict that `SolverService` persists.

This isolation means the solver can be upgraded (new CFR variant, better
sampling) by only touching `cfr_engine.py` + bumping `SOLVER_VERSION` in
`core/config.py` — every historical `solver_analysis` row stays attributable
to the version that produced it.

## 4. Opponent modeling

`opponent_service.py` implements the 4-tier classification
(NIT / TAG / LAG / MANIAC) from PFR + aggression rate, and exposes a
`jam_call_strategy()` lookup that widens/narrows jam-call ranges per tier.
This runs purely off the precomputed `opponent_profiles` row — no replay,
no solver call.

## 5. Caching layers

| Layer | What's cached | Invalidation |
|---|---|---|
| `RangeVsRangeEquityEngine._equity_cache` (in-process) | range-vs-range equity matrices | LRU eviction at 10k entries |
| `decision_snapshots.state_hash` (DB, transposition table) | full CFR solve result for a PBS | never (immutable once solved; new solver_version creates new rows) |
| `analytics_cache` (DB) | dashboard metrics | re-written by Celery task after each session import |
| Redis | Celery broker/result backend; can also front hot `GET /hands/{id}` reads | TTL-based |

## 6. Scaling notes

- `hands`/`hand_actions`/`solver_analysis`/`decision_snapshots` all carry
  `hand_id` as the join key with covering indexes — designed to stay fast
  into the billions-of-rows range (per the original schema notes).
- The Celery `solver` queue can be scaled horizontally (one worker per CPU
  core) independent of the API process, since CFR solving is the only
  bottleneck.
- `decision_snapshots` uses a GIN index over `hero_features`/
  `villain_features` JSONB columns for ad-hoc population queries
  (e.g. "all river spots with SPR 3–4 and nut_density > 0.3").

## 7. Service-to-table mapping

| Service | Table(s) |
|---|---|
| `HandService` | `hands`, `hand_actions` |
| `SolverService` | `solver_analysis`, `decision_snapshots` |
| `OpponentService` | `opponent_profiles` |
| `AnalyticsService` | `analytics_cache` |
| (future) `ReplayService` | `hand_actions` + `decision_snapshots` |
