import React, { useEffect, useMemo, useState } from "react";
import { fetchHistorical, fetchPrediction } from "./api";
import SymbolForm from "./components/SymbolForm";
import PredictionCard from "./components/PredictionCard";
import LiveTicker from "./components/LiveTicker";
import PredictionOverlayChart from "./components/PredictionOverlayChart";
import IndicatorsChart from "./components/IndicatorsChart";
import WatchlistPanel from "./components/WatchlistPanel";
import AlertsPanel from "./components/AlertsPanel";

const POPULAR_SYMBOLS = [
  "RELIANCE.NS",
  "TCS.NS",
  "INFY.NS",
  "HDFCBANK.NS",
  "ICICIBANK.NS",
  "SBIN.NS",
  "LT.NS",
  "ITC.NS",
  "BHARTIARTL.NS",
  "KOTAKBANK.NS",
  "HINDUNILVR.NS",
  "BAJFINANCE.NS",
  "AXISBANK.NS",
  "ASIANPAINT.NS",
  "MARUTI.NS",
  "TITAN.NS",
  "SUNPHARMA.NS",
  "ULTRACEMCO.NS"
];

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
  const [navActive, setNavActive] = useState("command");
  const [theme, setTheme] = useState(() => localStorage.getItem("sw_theme") || "light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("sw_theme", theme);
  }, [theme]);

  const previousClose = useMemo(() => {
    if (!history.length) {
      return null;
    }
    return history[history.length - 1].close;
  }, [history]);

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
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        "Request failed. Please try a valid stock symbol.";
      setError(message);
      setPrediction(null);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }

  function toggleTheme() {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }

  return (
    <div className="sw-root">
      <aside className="sw-sidebar">
        <SidebarBrand />
        <SidebarNav active={navActive} onSelect={setNavActive} />
        <div className="sw-sidebar-footer">
          <strong>Guest Mode</strong>
          <span className="sw-pill">No login required</span>
        </div>
      </aside>

      <div className="sw-main">
        <div className="sw-topbar">
          <h1>Markets desk</h1>
          <div className="sw-top-actions">
            <span className="sw-pill">Open access</span>
            <button type="button" className="theme-toggle-btn" onClick={toggleTheme}>
              {theme === "light" ? "Night" : "Light"}
            </button>
          </div>
        </div>

        <section className="sw-hero" id="sw-section-command">
          <div className="sw-hero-top">
            <div>
              <p className="kicker" style={{ marginBottom: 6 }}>Active symbol</p>
              <p className="sw-hero-symbol">{symbol}</p>
              <p className="sw-hero-tagline">
                Run a forecast to refresh OHLCV, hybrid models, and sentiment from headlines.
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
            quickSymbols={POPULAR_SYMBOLS}
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
          <PredictionOverlayChart historicalData={history} prediction={prediction} />
          <IndicatorsChart historicalData={history} />
        </div>
      </div>
    </div>
  );
}
