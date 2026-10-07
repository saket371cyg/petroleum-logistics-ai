# Viva / Final Submission Guide

## Project summary
This project is an offline-safe, dealer-facing petroleum logistics intelligence platform built as a full-stack agentic AI prototype. It blends a FastAPI backend, SQLAlchemy models, a React dashboard, and a rule-based decision layer that works without paid APIs or external keys.

## Core value proposition
- Demand forecasting from trained RandomForest models when available
- Offline fallback forecast if model files are missing
- Dispatch optimization using random-restart hill climbing
- Dealer-scoped security, tenant validation, and audit-friendly AI tool traces
- Synthetic but realistic logistics workflow for inventory, dispatch, compliance, and maintenance

## Demo flow
1. Log in with `dealer1@example.com` / `password123`
2. Open the Dashboard to review stock, alerts, and summary metrics
3. Visit Orders to get an order recommendation
4. Approve an order and optimize dispatch
5. Review the best-fit tanker, driver, loading slot, ETA, and cost explanation
6. Visit Compliance and Maintenance to review alerts and deadline risk
7. Use the AI assistant to ask operational questions using live dealer data

## Engineering notes
- Backend: FastAPI + SQLAlchemy + SQLite default, Postgres-compatible schema
- Frontend: React + Vite + Tailwind + Recharts
- AI: offline-first rule-based assistant with optional LLM integration behind a safe fallback
- Optimization: hill climbing with deterministic and benchmarked search behavior

## Verification commands
```bash
cd backend
.venv\Scripts\python.exe -m pytest -q

cd ../frontend
npm install
npm run build
```

## Evaluation angle
Explain that the project is not a mockup: it implements real data models, real workflows, and real offline decision logic. The architecture keeps each agent independent, making the system modular and easy to explain in a viva.

## Optional enhancement path
If a real Anthropic or other provider key becomes available later, the AI assistant can swap its fallback layer for a model-backed answer generator without changing the rest of the architecture.
