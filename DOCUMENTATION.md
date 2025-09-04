# PreBurn Technical Documentation

## Overview
PreBurn forecasts short‑term burnout risk and provides targeted actions to reduce it. The system combines a Python backend for risk modeling with Next.js frontend for an interactive, privacy‑aware experience.

## Technical Stack
- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI 
- Modeling: Lightweight in‑repo ML with optional Prophet forecasting; rule‑based fallbacks
- Data: CSV sample in `data/merged_burnout_schema_sample.csv` (daily grain)
- Dev/Build: Node 20+, Python 3.9+, uvicorn, Next.js dev server 

## Architecture
- Frontend calls `/api/*` which rewrites to the Python API via `next.config.ts`:
  - `source: /api/:path*` → `destination: http://127.0.0.1:8000/:path*`
- FastAPI serves risk, forecast, history, and actions endpoints
- Feature engineering and risk scoring live under `backend/models/*`.

### Backend Endpoints
- `GET /risk`: current risk score, level, and top contributors
- `GET /forecast`: 3‑day risk forecast (Prophet if available; else smoothing)
- `GET /history`: daily history with risk and key metrics
- `POST /ingest`: replace dataset (re-trains lightweight model)
- `GET /actions`:
  - Today (no `day`): uses LLM if configured; otherwise rules; ~3 concise actions for main scenarios
  - Future days: `GET /actions?day=N` (+1..+3) returns 1–2 varied, day‑specific actions via rules to avoid repetition

### Frontend UX
- Risk card with conic gauge and contributor chips.
- 3‑Day Forecast cards are clickable; clicking +Nd fetches `/api/actions?day=N` and updates the Actions list.
- Actions display title + one‑sentence explanation; includes loading and error states.

## Key Design Choices
1. FastAPI + Python
   - Clear expression of features (sleep debt, workload index, HRV/HR) and easy ML/rules switching.
2. Optional Prophet
   - Use when available; otherwise deterministic fallback for reliability and portability.
3. LLM‑optional recommendations
   - Today uses OpenAI if `OPENAI_API_KEY` is present; future days use deterministic rules to ensure non‑repetitive variety.
4. Forecast‑aligned actions
   - Recommendations tied to projected risk (+1..+3 days) instead of generic tips.
5. Frontend simplicity
   - Next.js App Router, client components where interactive, Tailwind for rapid, accessible styling.
6. Privacy & safety
   - Sample CSV only; no external user data. `.gitignore` excludes env/venv. History cleaned to remove a leaked env file.

## Data & Features (MVP)
- Inputs: sleep hours, resting HR(heart rate), HRV (RMSSD), steps, sentiment, meeting load
- Engineered: rolling z‑scores, sleep debt, workload index
- Outputs:
  - `risk_score` ∈ [0,1]
  - `risk_level`: Low / Medium / High
  - `top_contributors`: named drivers

## Error Handling & Fallbacks
- Forecast: Prophet → smoothing fallback
- Actions: LLM → rules fallback
- Frontend: loading state and error messages (no silent failures)

## Local Development
- Backend: `uvicorn backend.main:app --reload`
- Frontend: `cd frontend && npm install && npm run dev`
- Frontend dev server proxies `/api/*` to `127.0.0.1:8000`.

## Security Notes
- Do not commit secrets. Use env vars locally.
- `.gitignore` excludes common secret locations (e.g., `backend/.venv/.env`).
- Repo history rewritten to purge a previously committed env file.

## Future Work
- Data connectors (wearables, calendars, journaling)
- Stronger ML with evaluation and cross‑validation
- Explainability surfaced in UI (e.g., SHAP visuals)
- Personalization loop for action preferences
- Offline‑first mode and export
