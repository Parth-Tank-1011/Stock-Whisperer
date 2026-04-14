import React from "react";

export default function SymbolForm({ symbol, onSymbolChange, onSubmit, loading }) {
  return (
    <form className="symbol-form" onSubmit={onSubmit}>
      <label htmlFor="symbol">Stock Symbol (NSE/BSE)</label>
      <div className="symbol-controls">
        <input
          id="symbol"
          type="text"
          value={symbol}
          onChange={(event) => onSymbolChange(event.target.value)}
          placeholder="RELIANCE.NS"
          autoComplete="off"
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? "Predicting..." : "Predict"}
        </button>
      </div>
      <p className="hint">Examples: RELIANCE.NS, TCS.NS, INFY.NS, SBIN.NS</p>
    </form>
  );
}
