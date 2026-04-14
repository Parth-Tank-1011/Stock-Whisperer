import React from "react";
import {
  CartesianGrid,
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
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
  }).format(value);
}

export default function PriceChart({ data }) {
  if (!data || data.length === 0) {
    return null;
  }

  const recent = data.slice(-120).map((item) => ({
    date: item.date,
    close: Number(item.close.toFixed(2))
  }));

  return (
    <section className="chart-card">
      <h2>Recent Close Prices</h2>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={recent}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
            <XAxis dataKey="date" tickFormatter={formatDate} minTickGap={20} />
            <YAxis domain={["auto", "auto"]} tickFormatter={(value) => `${value}`} />
            <Tooltip
              formatter={(value) => formatINR(value)}
              labelFormatter={(label) => new Date(label).toDateString()}
            />
            <Line
              type="monotone"
              dataKey="close"
              stroke="#0f766e"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
