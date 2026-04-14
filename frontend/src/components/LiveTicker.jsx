import React, { useEffect, useMemo, useState } from "react";
import { fetchLivePrice } from "../api";

function formatPrice(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "-";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(Number(value));
}

export default function LiveTicker({ symbol, refreshMs = 5000 }) {
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState("");

  const trendClass = useMemo(() => {
    if (!quote) {
      return "flat";
    }
    return quote.change >= 0 ? "up" : "down";
  }, [quote]);

  useEffect(() => {
    if (!symbol) {
      return undefined;
    }

    let cancelled = false;

    async function loadQuote() {
      try {
        const data = await fetchLivePrice(symbol);
        if (!cancelled) {
          setQuote(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.detail || "Live quote unavailable");
        }
      }
    }

    loadQuote();
    const id = setInterval(loadQuote, refreshMs);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [symbol, refreshMs]);

  return (
    <section className="live-ticker chart-card">
      <div className="live-header">
        <h2>Live Price</h2>
        <span className="live-badge">Auto refresh {Math.round(refreshMs / 1000)}s</span>
      </div>

      {error ? <p className="live-error">{error}</p> : null}

      <div className="live-grid">
        <div>
          <span>Symbol</span>
          <strong>{quote?.exchange_symbol || symbol}</strong>
        </div>
        <div>
          <span>Price</span>
          <strong>{formatPrice(quote?.price)}</strong>
        </div>
        <div>
          <span>Change</span>
          <strong className={trendClass}>
            {quote ? `${quote.change >= 0 ? "+" : ""}${Number(quote.change).toFixed(2)}` : "-"}
          </strong>
        </div>
        <div>
          <span>Change %</span>
          <strong className={trendClass}>
            {quote ? `${quote.change_percent >= 0 ? "+" : ""}${Number(quote.change_percent).toFixed(2)}%` : "-"}
          </strong>
        </div>
        <div>
          <span>Updated</span>
          <strong>{quote?.timestamp ? new Date(quote.timestamp).toLocaleTimeString() : "-"}</strong>
        </div>
      </div>
    </section>
  );
}
