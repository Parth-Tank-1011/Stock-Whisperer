# Indian Stock Price Prediction Backend (FastAPI + ML)

Production-ready backend for Indian stock prediction using Yahoo Finance and a hybrid forecasting stack.

## Features
- Historical data fetch for NSE/BSE symbols (example: `RELIANCE.NS`, `TCS.NS`)
- Data preprocessing with missing value handling, scaling, and technical indicators
- Features used by the model:
  - OHLCV: `Open`, `High`, `Low`, `Close`, `Volume`
  - Indicators: `RSI`, `MACD`, `MACD_SIGNAL`, `SMA_20`, `EMA_20`
- Multi-day forecasts from `/predict`:
  - `1d` (next day)
  - `3d`
  - `7d`
- Hybrid model comparison pipeline:
  - Random Forest (enabled by default)
  - GRU + LSTM (optional, enable via env)
  - XGBoost (optional, enable via env)
- Best-model selection by validation RMSE
- Caching for historical API responses
- Model/scaler persistence and conditional retraining
- Structured error handling and logging
- CORS enabled for React frontend integration

## Security & Production Hardening
- In-memory IP-based rate limiting middleware (`429` with `Retry-After`)
- Input validation for symbols, auth payloads, and request schemas
- Request logging middleware with request ID (`X-Request-ID`) and latency
- Rotating application logs at `storage/logs/app.log`
- External API retry handling for Yahoo calls (historical/live/news)
- Alert check endpoint degrades gracefully when quote fetch fails per-symbol

## Folder Structure
- `backend/app/main.py` - FastAPI entrypoint
- `backend/app/routes` - API routes
- `backend/app/services` - Business logic and ML orchestration
- `backend/app/models` - Request/response schemas
- `backend/app/utils` - Shared helper utilities (symbol normalization, formatting)
- `backend/storage/models` - Saved model and scaler artifacts
- `backend/storage/meta` - Model training metadata
- `frontend` - React UI dashboard

## Run Backend Locally
```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Run Frontend Locally
```bash
cd frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Frontend opens on `http://localhost:5173` and connects to backend at `http://127.0.0.1:8000`.

## Optional model toggles (`.env`)
```bash
ENABLE_DEEP_MODELS=false   # LSTM + GRU
ENABLE_XGBOOST=false       # XGBoost benchmark
```

Set to `true` when you want deeper benchmarking, then restart backend.

## Production knobs (`.env`)
```bash
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_REQUESTS=80
REQUEST_LOG_ENABLED=true
EXTERNAL_API_RETRIES=2
EXTERNAL_API_RETRY_DELAY_MS=400
LOG_DIR=storage/logs
```

## API Endpoints
- `GET /health`
- `GET /stock/{symbol}`
- `GET /predict/{symbol}`

Example response (`/predict/RELIANCE.NS`):
```json
{
  "stock": "RELIANCE",
  "predicted_price": 1318.56,
  "prediction": "DOWN",
  "trend": "DOWN",
  "confidence": 0.9797,`r`n  "rmse": 27.3064,`r`n  "accuracy_percent": 97.93,
  "sentiment": "NEUTRAL",
  "sentiment_score": 0.0,
  "headlines_analyzed": 0,
  "suggestion": "HOLD",
  "horizon_predictions": {
    "1d": 1318.56,
    "3d": 1319.92,
    "7d": 1317.85
  },
  "model_used": "random_forest",
  "model_metrics": {
    "random_forest": 27.3064
  }
}
```

## Docker (full stack: API + built UI on one port)

The image builds the Vite app and serves it from FastAPI when `FRONTEND_DIST_DIR` is set (the Dockerfile sets it to `/app/frontend/dist`).

```bash
docker build -f backend/Dockerfile -t stock-whisperer .
docker run --rm -p 8000:8000 -e JWT_SECRET_KEY="use-a-long-random-secret" stock-whisperer
```

Open `http://localhost:8000` for the UI; `http://localhost:8000/docs` for OpenAPI.

**Compose (optional):** `docker compose up --build` from the repo root uses `docker-compose.yml`. Put secrets in a local `.env` file (see `.env.example`).

**Split hosting:** deploy the API container only, build the frontend with `VITE_API_BASE_URL=https://your-api.example.com`, and host `frontend/dist` on any static host (S3, Netlify, etc.).

For this project deployment:
- Frontend: `https://stock-whisperer-sigma.vercel.app/`
- Backend: `https://stock-whisperer-1.onrender.com/`

Set these variables:
- Vercel (Frontend): `VITE_API_BASE_URL=https://stock-whisperer-1.onrender.com`
- Render (Backend): `CORS_ORIGINS=https://stock-whisperer-sigma.vercel.app`
- Render (Backend, optional): `FRONTEND_URL=https://stock-whisperer-sigma.vercel.app`
- Render (Backend persistence): attach a persistent disk and set `DATABASE_URL=sqlite:////var/data/stock_whisperer.db` (or use Postgres)

## Product Features API (Auth, Watchlist, Alerts)

### Auth
- `POST /auth/signup`
  ```json
  {
    "username": "parth",
    "email": "parth@example.com",
    "password": "Pass1234!"
  }
  ```
- `POST /auth/login`
  ```json
  {
    "username": "parth",
    "password": "Pass1234!"
  }
  ```
- `GET /auth/me` (Bearer token required)

### Watchlist
- `GET /watchlist`
- `POST /watchlist`
  ```json
  { "symbol": "RELIANCE.NS" }
  ```
- `DELETE /watchlist/{symbol}`

### Alerts
- `GET /alerts`
- `POST /alerts`
  ```json
  {
    "symbol": "RELIANCE.NS",
    "target_price": 3000,
    "direction": "ABOVE"
  }
  ```
- `POST /alerts/check`
- `DELETE /alerts/{alert_id}`

### Valid stock symbol input examples
- `RELIANCE.NS`
- `TCS.NS`
- `INFY.NS`
- `HDFCBANK.NS`
- `SBIN.NS`
- BSE symbols can use `.BO`, for example `RELIANCE.BO`

## AI Sentiment + Suggestion
`GET /predict/{symbol}` now also returns:
- `prediction`: `UP` or `DOWN`
- `sentiment`: `POSITIVE` / `NEGATIVE` / `NEUTRAL`
- `sentiment_score`: range `-1` to `1`
- `suggestion`: `BUY` / `SELL` / `HOLD`
- `headlines_analyzed`: number of headlines used
