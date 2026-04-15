import axios from "axios";

function resolveApiBaseUrl() {
  const fromEnv = import.meta.env.VITE_API_BASE_URL;
  if (fromEnv != null && String(fromEnv).trim() !== "") {
    return String(fromEnv).trim();
  }
  // Production bundle served from FastAPI: same-origin. Dev: Vite on 5173 → backend 8000.
  return import.meta.env.PROD
    ? "https://stock-whisperer-1.onrender.com"
    : "http://127.0.0.1:8000";
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 120000
});

export async function fetchHistorical(symbol) {
  const response = await api.get(`/stock/${encodeURIComponent(symbol)}`);
  return response.data;
}

export async function fetchLivePrice(symbol) {
  const response = await api.get(`/live/${encodeURIComponent(symbol)}`);
  return response.data;
}

export async function fetchPrediction(symbol) {
  const response = await api.get(`/predict/${encodeURIComponent(symbol)}`, {
    timeout: 180000
  });
  return response.data;
}

export async function fetchWatchlist() {
  const response = await api.get("/watchlist");
  return response.data;
}

export async function fetchWatchlistQuotes() {
  const response = await api.get("/watchlist/quotes");
  return response.data;
}

export async function addWatchlist(symbol) {
  const response = await api.post("/watchlist", { symbol });
  return response.data;
}

export async function removeWatchlist(symbol) {
  const response = await api.delete(`/watchlist/${encodeURIComponent(symbol)}`);
  return response.data;
}

export async function fetchAlerts() {
  const response = await api.get("/alerts");
  return response.data;
}

export async function addAlert(payload) {
  const response = await api.post("/alerts", payload);
  return response.data;
}

export async function removeAlert(alertId) {
  const response = await api.delete(`/alerts/${alertId}`);
  return response.data;
}

export async function checkAlerts() {
  const response = await api.post("/alerts/check");
  return response.data;
}
