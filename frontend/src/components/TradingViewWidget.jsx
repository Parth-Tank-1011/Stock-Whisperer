import React, { useEffect, useMemo, useRef } from "react";

function toTradingViewSymbol(symbol) {
  const normalized = (symbol || "").trim().toUpperCase();

  if (!normalized) {
    return "NSE:RELIANCE";
  }

  if (normalized.includes(":")) {
    return normalized;
  }

  if (normalized.endsWith(".NS")) {
    const code = normalized.slice(0, -3);
    return `NSE:${code}`;
  }

  if (normalized.endsWith(".BO")) {
    const code = normalized.slice(0, -3);
    // TradingView usually expects numeric BSE codes. For company aliases, NSE fallback is safer.
    if (/^\d+$/.test(code)) {
      return `BSE:${code}`;
    }
    return `NSE:${code}`;
  }

  // Default unresolved Indian symbol to NSE.
  return `NSE:${normalized}`;
}

export default function TradingViewWidget({ symbol }) {
  const containerRef = useRef(null);
  const widgetContainerId = useMemo(
    () => `tradingview_${Math.random().toString(36).slice(2, 9)}`,
    []
  );

  useEffect(() => {
    const tradingViewSymbol = toTradingViewSymbol(symbol);

    function mountWidget() {
      if (!window.TradingView || !containerRef.current) {
        return;
      }

      containerRef.current.innerHTML = `<div id="${widgetContainerId}" style="height:100%;width:100%"></div>`;

      // Candlestick chart with professional interactions powered by TradingView.
      // eslint-disable-next-line no-new
      new window.TradingView.widget({
        autosize: true,
        symbol: tradingViewSymbol,
        interval: "D",
        timezone: "Asia/Kolkata",
        theme: "dark",
        style: "1",
        locale: "en",
        hide_top_toolbar: false,
        hide_side_toolbar: false,
        allow_symbol_change: true,
        container_id: widgetContainerId
      });
    }

    if (window.TradingView) {
      mountWidget();
      return;
    }

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/tv.js";
    script.async = true;
    script.onload = mountWidget;
    document.body.appendChild(script);

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [symbol, widgetContainerId]);

  return (
    <section className="chart-card">
      <h2>Candlestick Chart</h2>
      <div className="tv-chart-wrap" ref={containerRef} />
    </section>
  );
}
