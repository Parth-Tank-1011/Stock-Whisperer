import React from "react";

function formatPrice(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(value);
}

export default function PredictionCard({ prediction, previousClose }) {
  if (!prediction) {
    return null;
  }

  const trendClass = prediction.trend === "UP" ? "up" : "down";
  const suggestionClass =
    prediction.suggestion === "BUY"
      ? "up"
      : prediction.suggestion === "SELL"
        ? "down"
        : "flat";

  const horizonPredictions = prediction.horizon_predictions || {};
  const modelMetrics = prediction.model_metrics || {};
  const modelAccuracy = prediction.model_accuracy || {};

  return (
    <section className="prediction-card">
      <h2>Prediction Result</h2>
      <div className="prediction-grid">
        <div>
          <span>Stock</span>
          <strong>{prediction.stock}</strong>
        </div>
        <div>
          <span>Predicted Close (1D)</span>
          <strong>{formatPrice(prediction.predicted_price)}</strong>
        </div>
        <div>
          <span>Previous Close</span>
          <strong>{formatPrice(previousClose)}</strong>
        </div>
        <div>
          <span>Trend</span>
          <strong className={trendClass}>{prediction.trend}</strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>{Math.round((prediction.confidence || 0) * 100)}%</strong>
        </div>
      </div>

      <div className="subsection">
        <h3>Model Accuracy Metrics</h3>
        <div className="prediction-grid forecast-grid">
          <div>
            <span>RMSE (Best Model)</span>
            <strong>{Number(prediction.rmse || 0).toFixed(2)}</strong>
          </div>
          <div>
            <span>Accuracy % (Best Model)</span>
            <strong>{Number(prediction.accuracy_percent || 0).toFixed(2)}%</strong>
          </div>
          <div>
            <span>Best Model</span>
            <strong>{prediction.model_used || "-"}</strong>
          </div>
        </div>
      </div>

      <div className="subsection">
        <h3>AI Decision Layer</h3>
        <div className="prediction-grid forecast-grid">
          <div>
            <span>Sentiment</span>
            <strong>{prediction.sentiment || "NEUTRAL"}</strong>
          </div>
          <div>
            <span>Sentiment Score</span>
            <strong>{Number(prediction.sentiment_score || 0).toFixed(2)}</strong>
          </div>
          <div>
            <span>Suggestion</span>
            <strong className={suggestionClass}>{prediction.suggestion || "HOLD"}</strong>
          </div>
        </div>
        <p className="model-used">Headlines analyzed: <strong>{prediction.headlines_analyzed || 0}</strong></p>
      </div>

      <div className="subsection">
        <h3>Multi-day Forecast</h3>
        <div className="prediction-grid forecast-grid">
          <div>
            <span>1 Day</span>
            <strong>{formatPrice(horizonPredictions["1d"])}</strong>
          </div>
          <div>
            <span>3 Days</span>
            <strong>{formatPrice(horizonPredictions["3d"])}</strong>
          </div>
          <div>
            <span>7 Days</span>
            <strong>{formatPrice(horizonPredictions["7d"])}</strong>
          </div>
        </div>
      </div>

      <div className="subsection">
        <h3>Model Comparison</h3>
        <div className="metrics-row">
          {Object.entries(modelMetrics).map(([modelName, rmse]) => (
            <div key={modelName} className="metric-pill">
              <span>{modelName}</span>
              <strong>{Number(rmse).toFixed(2)} RMSE | {Number(modelAccuracy[modelName] || 0).toFixed(2)}%</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
