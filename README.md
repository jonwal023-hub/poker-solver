# Poker Solver Platform

A full-stack poker analytics platform built around a custom **ReBeL-style CFR solver**
(three-reach probability CFR + range-vs-range equity engine), with opponent modeling,
hand history storage, and instant hand-review (no solver re-runs on read).

```
poker-solver-platform/
├── backend/        FastAPI service: REST API, solver orchestration, DB access
├── frontend/        React + TypeScript SPA: session/hand review, dashboards
├── database/        PostgreSQL schema, migrations, seed data
├── docs/             Architecture, API contracts, ERD
├── docker-compose.yml
└── .github/workflows/  CI (lint, test, build)
```

## Core Idea

> **Solve once, read forever.**

The solver is expensive (Monte Carlo + CFR tree search). The schema is designed so the
solver only ever runs **once per hand**, and every result (`recommended_action`,
`ev_loss`, the compressed `PublicBeliefState` snapshot) is persisted. The frontend never
triggers a solve on a normal page view — `GET /hands/{id}` is a single indexed query
(see `database/migrations/0001_init.sql` → `hand_review` view).

## Stack

| Layer        | Choice                                   | Why |
|--------------|-------------------------------------------|-----|
| Backend      | FastAPI (Python 3.11+), SQLAlchemy 2.0, Alembic | Same language as the solver — zero serialization tax between solver and API layer |
| Database     | PostgreSQL 15 (JSONB + GIN indexes)       | Structured relational tables + flexible compressed feature vectors in one engine |
| Cache/Queue  | Redis (cache) + Celery/RQ (async solver jobs) | Solver runs are CPU-heavy; never block the request thread |
| Frontend     | React 18 + TypeScript + Vite, TanStack Query, Zustand, Recharts | Type-safe, fast dev loop, good chart support for equity/EV graphs |
| Solver       | Existing Python CFR/ReBeL engine (untouched) | Wrapped, not rewritten — see `backend/app/solver/` |

## Quickstart

```bash
cp .env.example .env
docker compose up --build
# backend:  http://localhost:8000/docs
# frontend: http://localhost:5173
```

## Repo Map

- `database/migrations/0001_init.sql` — locked v2.0 production schema (users → sessions → hands → hand_actions/solver_analysis/decision_snapshots, opponent_profiles, analytics_cache)
- `backend/app/solver/engine_adapter.py` — adapter around the existing `CorrectedSolverBot` (three-reach CFR + range equity engine), translates DB rows ↔ solver objects
- `backend/app/services/` — one service per domain table (`HandService`, `SolverService`, `OpponentService`, `AnalyticsService`, `ReplayService`)
- `frontend/src/pages/HandReview.tsx` — single-query hand replay + EV-loss overlay
- `docs/ARCHITECTURE.md` — full system design, data flow, scaling notes
