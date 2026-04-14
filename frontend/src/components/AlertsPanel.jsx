import React, { useEffect, useState } from "react";
import { addAlert, checkAlerts, fetchAlerts, removeAlert } from "../api";

export default function AlertsPanel({ activeSymbol }) {
  const [alerts, setAlerts] = useState([]);
  const [symbol, setSymbol] = useState(activeSymbol || "");
  const [targetPrice, setTargetPrice] = useState("");
  const [direction, setDirection] = useState("ABOVE");
  const [error, setError] = useState("");
  const [triggered, setTriggered] = useState([]);

  async function loadAlerts() {
    try {
      const data = await fetchAlerts();
      setAlerts(data.items || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load alerts");
    }
  }

  async function pollAlerts() {
    try {
      const checked = await checkAlerts();
      const hits = (checked.results || []).filter((item) => item.triggered);
      if (hits.length) {
        setTriggered(hits);
        await loadAlerts();
      }
    } catch {
      // no-op to keep polling resilient
    }
  }

  useEffect(() => {
    loadAlerts();
  }, []);

  useEffect(() => {
    const id = setInterval(pollAlerts, 7000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (activeSymbol) {
      setSymbol(activeSymbol);
    }
  }, [activeSymbol]);

  async function addItem(event) {
    event.preventDefault();
    const normalized = symbol.trim().toUpperCase();

    try {
      await addAlert({
        symbol: normalized,
        target_price: Number(targetPrice),
        direction
      });
      setTargetPrice("");
      setError("");
      await loadAlerts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create alert");
    }
  }

  async function deleteItem(alertId) {
    try {
      await removeAlert(alertId);
      await loadAlerts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to delete alert");
    }
  }

  return (
    <section className="chart-card">
      <h2>Price Alerts</h2>
      <form className="auth-form alerts-form" onSubmit={addItem}>
        <input
          type="text"
          value={symbol}
          onChange={(event) => setSymbol(event.target.value)}
          placeholder="Symbol"
          required
        />
        <input
          type="number"
          value={targetPrice}
          onChange={(event) => setTargetPrice(event.target.value)}
          placeholder="Target price"
          step="0.01"
          required
        />
        <select value={direction} onChange={(event) => setDirection(event.target.value)}>
          <option value="ABOVE">ABOVE</option>
          <option value="BELOW">BELOW</option>
        </select>
        <button type="submit">Create Alert</button>
      </form>

      {error ? <p className="live-error">{error}</p> : null}

      {triggered.length ? (
        <div className="triggered-box">
          {triggered.map((item) => (
            <p key={item.alert_id}>
              Alert hit: {item.symbol} {item.direction} {item.target_price}
              {item.current_price != null ? ` (now ${Number(item.current_price).toFixed(2)})` : ""}
            </p>
          ))}
        </div>
      ) : null}

      <div className="list-wrap">
        {alerts.map((alert) => (
          <div key={alert.id} className="list-row">
            <span>
              {alert.symbol} {alert.direction} {Number(alert.target_price).toFixed(2)} [{alert.is_active ? "ACTIVE" : "DONE"}]
            </span>
            <button type="button" className="danger-btn" onClick={() => deleteItem(alert.id)}>
              Delete
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
