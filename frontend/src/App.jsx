import React, { useCallback, useEffect, useMemo, useState } from "react";
import { fetchHistorical, fetchMe, fetchPrediction } from "./api";
import SymbolForm from "./components/SymbolForm";
import PredictionCard from "./components/PredictionCard";
import LiveTicker from "./components/LiveTicker";
import TradingViewWidget from "./components/TradingViewWidget";
import PredictionOverlayChart from "./components/PredictionOverlayChart";
import IndicatorsChart from "./components/IndicatorsChart";
import AuthPanel from "./components/AuthPanel";
import WatchlistPanel from "./components/WatchlistPanel";
import AlertsPanel from "./components/AlertsPanel";

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function SidebarBrand() {
  return (
    <div className="sw-brand">
      <p className="sw-brand-mark">Indian markets</p>
      <h2 className="sw-brand-title">Stock Whisperer</h2>
      <p className="sw-brand-sub">Forecasts, sentiment, and live NSE/BSE tooling.</p>
    </div>
  );
}

function SidebarNav({ active, onSelect }) {
  const items = [
    { id: "sw-section-command", key: "command", label: "Command" },
    { id: "sw-section-portfolio", key: "portfolio", label: "Watchlist & alerts" },
    { id: "sw-section-analytics", key: "analytics", label: "Analytics" }
  ];

  return (
    <nav className="sw-nav" aria-label="Primary">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          className={active === item.key ? "active" : ""}
          onClick={() => {
            onSelect(item.key);
            scrollToSection(item.id);
          }}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}

export default function App() {
  const [symbol, setSymbol] = useState("RELIANCE.NS");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [navActive, setNavActive] = useState("command");

  const previousClose = useMemo(() => {
    if (!history.length) {
      return null;
    }
    return history[history.length - 1].close;
  }, [history]);

  const loadProfile = useCallback(async () => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setUser(null);
      setAuthChecked(true);
      return;
    }

    try {
      const me = await fetchMe();
      setUser(me);
    } catch {
      localStorage.removeItem("auth_token");
      setUser(null);
    } finally {
      setAuthChecked(true);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  async function handleSubmit(event) {
    event.preventDefault();
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [historicalData, predictionData] = await Promise.all([
        fetchHistorical(normalized),
        fetchPrediction(normalized)
      ]);

      setHistory(historicalData.data || []);
      setPrediction(predictionData);
      setSymbol(normalized);
    } catch (err) {
      const message = err?.response?.data?.detail || err?.message || "Request failed. Please try a valid stock symbol.";
      setError(message);
      setPrediction(null);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("auth_token");
    setUser(null);
  }

  if (!authChecked) {
    return (
      <div className="sw-root">
        <div className="sw-main" style={{ maxWidth: 560, margin: "0 auto", justifyContent: "center" }}>
          <section className="chart-card">Checking session…</section>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="sw-root">
        <aside className="sw-sidebar">
          <SidebarBrand />
          <div className="sw-sidebar-footer">
            <span className="sw-chip">Secure workspace</span>
            <p style={{ margin: "12px 0 0", fontSize: "0.82rem", color: "var(--muted)" }}>
              Sign in to sync watchlists, alerts, and saved preferences.
            </p>
          </div>
        </aside>
        <div className="sw-main">
          <header>
            <p className="kicker">NSE · BSE</p>
            <h1>Welcome to Stock Whisperer</h1>
            <p className="subtitle">Login or create an account for watchlist, price alerts, and ML forecasts.</p>
          </header>
          <AuthPanel onAuthenticated={loadProfile} />
        </div>
      </div>
    );
  }

  return (
    <div className="sw-root">
      <aside className="sw-sidebar">
        <SidebarBrand />
        <SidebarNav active={navActive} onSelect={setNavActive} />
        <div className="sw-sidebar-footer">
          <strong>{user.username}</strong>
          <span className="sw-pill">Session active</span>
        </div>
      </aside>

      <div className="sw-main">
        <div className="sw-topbar">
          <h1>Markets desk</h1>
          <div className="sw-top-actions">
            <span className="sw-pill">Signed in</span>
            <button type="button" className="logout-btn" onClick={logout}>
              Logout
            </button>
          </div>
        </div>

        <section className="sw-hero" id="sw-section-command">
          <div className="sw-hero-top">
            <div>
              <p className="kicker" style={{ marginBottom: 6 }}>Active symbol</p>
              <p className="sw-hero-symbol">{symbol}</p>
              <p className="sw-hero-tagline">
                Run a forecast to refresh OHLCV, hybrid models, sentiment from headlines, and TradingView context.
              </p>
            </div>
            <div className="sw-hero-meta">
              <span className="sw-chip">Live quotes</span>
              <span className="sw-chip">Multi-horizon</span>
              <span className="sw-chip">Alerts</span>
            </div>
          </div>
          <SymbolForm
            symbol={symbol}
            onSymbolChange={setSymbol}
            onSubmit={handleSubmit}
            loading={loading}
          />
        </section>

        {error ? <div className="error-banner">{error}</div> : null}

        <div id="sw-section-portfolio">
          <div className="product-grid">
            <WatchlistPanel onSelectSymbol={setSymbol} />
            <AlertsPanel activeSymbol={symbol} />
          </div>
        </div>

        <div id="sw-section-analytics">
          <LiveTicker symbol={symbol} refreshMs={5000} />
          <PredictionCard prediction={prediction} previousClose={previousClose} />
          <TradingViewWidget symbol={symbol} />
          <PredictionOverlayChart historicalData={history} prediction={prediction} />
          <IndicatorsChart historicalData={history} />
        </div>
      </div>
    </div>
  );
}
