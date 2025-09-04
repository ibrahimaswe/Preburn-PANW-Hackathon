# 🔥 PreBurn: Predict Burnout Before It Hits

> **“Your sleep app, your calendar, and your heart rate don’t talk.  
> PreBurn connects them to forecast burnout risk and tell you what to do—before you crash.”**

---

## 🚀 Overview
PreBurn is a **Personal Health & Wellness Aggregator** that unifies **sleep, activity, biometrics, journaling sentiment, and workload data** into a single daily risk score.  
Instead of just showing numbers, it provides **personalized, preventive nudges** that reduce burnout risk and keep you in balance.

---

## ✨ Features
- **Risk Gauge** → Daily burnout risk (Low / Medium / High).  
- **Why Now Chips** → Top 2–3 contributors (e.g., “Sleep debt ↑”, “After-hours meetings”, “Sentiment ↓”).  
- **Personalized Nudges** → One-tap actions like a breathing exercise, short walk, or meeting reschedule suggestion.  
- **7-Day Trend & 3-Day Forecast** → See patterns and what’s ahead.  
- **Data Unification** → Sleep, HR, HRV, steps, sentiment, and calendar workload fused into one dashboard.  
- **Privacy First** → Read-only connectors, local processing, and delete-anytime controls.

---

## 🧩 Architecture
**Frontend**
- [Next.js](https://nextjs.org/) + [Tailwind](https://tailwindcss.com/)  
- [Recharts](https://recharts.org/) for visualizations (risk gauge, trends)

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) (Python) or [Express](https://expressjs.com/) (Node.js)  
- Endpoints:
  - `POST /ingest` → upload CSV or JSON (daily metrics)  
  - `GET /risk` → current risk + top contributors  
  - `GET /forecast` → next 3 days risk trend  
  - `GET /explain` → feature importances  

**Data**
- Unified schema (daily grain) with sleep, HR/HRV, steps, sentiment, meetings.  
- Example file: [`merged_burnout_schema_sample.csv`](./data/merged_burnout_schema_sample.csv)

---

## 📊 Risk Model (MVP)
- **Inputs**: sleep hours, resting HR, HRV, steps, journaling sentiment, meeting load.  
- **Features**: rolling 7-day z-scores, sleep debt, workload index.  
- **Output**:  
  - `risk_score` ∈ [0,1]  
  - `risk_level`: Low (<0.33), Medium (0.33–0.66), High (>0.66)  
  - `top_contributors`: key drivers today  

---

## 🛠️ Setup
Clone the repo:
```bash
git clone https://github.com/yourusername/preburn.git
cd preburn
