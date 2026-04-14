import React, { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

function formatDate(value) {
  const date = new Date(value);
  return `${date.getDate()}/${date.getMonth() + 1}`;
}

function formatINR(value) {
  if (value == null) {
    return "-";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(value);
}

function addDays(isoDate, days) {
  const date = new Date(isoDate);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export default function PredictionOverlayChart({ historicalData, prediction }) {
  const chartData = useMemo(() => {
    if (!historicalData?.length) {
      return [];
    }

    const recent = historicalData.slice(-90).map((item) => ({
      date: item.date,
      close: Number(item.close),
      forecast: null
    }));

    if (!prediction?.horizon_predictions) {
      return recent;
    }

    const lastDate = recent[recent.length - 1].date;
    const futurePoints = [
      { date: addDays(lastDate, 1), forecast: prediction.horizon_predictions["1d"] ?? null },
      { date: addDays(lastDate, 3), forecast: prediction.horizon_predictions["3d"] ?? null },
      { date: addDays(lastDate, 7), forecast: prediction.horizon_predictions["7d"] ?? null }
    ].map((point) => ({
      date: point.date,
      close: null,
      forecast: point.forecast != null ? Number(point.forecast) : null
    }));

    return [...recent, ...futurePoints];
  }, [historicalData, prediction]);

  if (!chartData.length) {
    return null;
  }

  const axisStyle = { fill: "#94a3b8", fontSize: 11 };
  const tooltipStyle = {
    backgroundColor: "#0f172a",
    border: "1px solid #334155",
    borderRadius: 8,
    color: "#e2e8f0"
  };

  return (
    <section className="chart-card">
      <h2>Prediction Overlay</h2>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tickFormatter={formatDate} minTickGap={20} stroke="#475569" tick={axisStyle} />
            <YAxis domain={["auto", "auto"]} stroke="#475569" tick={axisStyle} />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) => formatINR(value)}
              labelFormatter={(label) => new Date(label).toDateString()}
            />
            <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
            <Line
              type="monotone"
              dataKey="close"
              stroke="#22d3ee"
              strokeWidth={2.2}
              dot={false}
              name="Historical Close"
            />
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#fb923c"
              strokeWidth={2.4}
              strokeDasharray="6 4"
              dot={{ r: 3 }}
              name="Forecast (1d/3d/7d)"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
