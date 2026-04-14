import React, { useEffect, useState } from "react";
import { addWatchlist, fetchWatchlist, fetchWatchlistQuotes, removeWatchlist } from "../api";

function formatInr(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "—";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(Number(value));
}

export default function WatchlistPanel({ onSelectSymbol }) {
  const [items, setItems] = useState([]);
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState("");
  const [quotesBySymbol, setQuotesBySymbol] = useState({});

  async function load() {
    try {
      const data = await fetchWatchlist();
      setItems(data.items || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load watchlist");
    }
  }

  async function loadQuotes() {
    if (!items.length) {
      setQuotesBySymbol({});
      return;
    }
    try {
      const data = await fetchWatchlistQuotes();
      const map = {};
      (data.items || []).forEach((row) => {
        map[row.symbol] = row;
      });
      setQuotesBySymbol(map);
    } catch {
      // keep last good snapshot; avoid noisy UI on transient failures
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    loadQuotes();
  }, [items]);

  useEffect(() => {
    if (!items.length) {
      return undefined;
    }
    const id = setInterval(loadQuotes, 12000);
    return () => clearInterval(id);
  }, [items]);

  async function addItem(event) {
    event.preventDefault();
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) {
      return;
    }

    try {
      await addWatchlist(normalized);
      setSymbol("");
      setError("");
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to add symbol");
    }
  }

  async function removeItem(targetSymbol) {
    try {
      await removeWatchlist(targetSymbol);
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to remove symbol");
    }
  }

  return (
    <section className="chart-card">
      <h2>Watchlist</h2>
      <form className="auth-form watchlist-form" onSubmit={addItem}>
        <input
          type="text"
          value={symbol}
          onChange={(event) => setSymbol(event.target.value)}
          placeholder="Add symbol (e.g. INFY.NS)"
        />
        <button type="submit">Add</button>
      </form>

      {error ? <p className="live-error">{error}</p> : null}

      <div className="list-wrap">
        {items.map((item) => {
          const row = quotesBySymbol[item.symbol];
          const q = row?.quote;
          const quoteLine = q
            ? `${formatInr(q.price)} · ${q.change_percent >= 0 ? "+" : ""}${Number(q.change_percent).toFixed(2)}%`
            : row?.error || (items.length ? "Loading quote…" : null);

          return (
            <div key={item.id} className="list-row">
              <div className="watchlist-row-main">
                <button type="button" className="symbol-chip" onClick={() => onSelectSymbol?.(item.symbol)}>
                  {item.symbol}
                </button>
                {quoteLine ? (
                  <span className="watchlist-quote">
                    <strong>LTP</strong> {quoteLine}
                  </span>
                ) : null}
              </div>
              <button type="button" className="danger-btn" onClick={() => removeItem(item.symbol)}>
                Remove
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
