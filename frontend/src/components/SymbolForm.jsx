import React from "react";

export default function SymbolForm({ symbol, onSymbolChange, onSubmit, loading, quickSymbols = [] }) {
  const datalistId = "popular-symbols";

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
          list={datalistId}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? "Predicting..." : "Predict"}
        </button>
      </div>
      {quickSymbols.length ? (
        <>
          <datalist id={datalistId}>
            {quickSymbols.map((item) => (
              <option key={item} value={item} />
            ))}
          </datalist>
          <div className="symbol-picks" aria-label="Popular symbols">
            {quickSymbols.map((item) => (
              <button
                key={item}
                type="button"
                className="symbol-pick-btn"
                onClick={() => onSymbolChange(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </>
      ) : null}
      <p className="hint">Popular picks: RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS, LT.NS</p>
    </form>
  );
}
