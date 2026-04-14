import React, { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

function sma(values, period, idx) {
  if (idx < period - 1) {
    return null;
  }
  let sum = 0;
  for (let i = idx - period + 1; i <= idx; i += 1) {
    sum += values[i];
  }
  return sum / period;
}

function ema(values, period) {
  const out = [];
  const multiplier = 2 / (period + 1);
  let prev = values[0] ?? 0;

  for (let i = 0; i < values.length; i += 1) {
    const value = values[i];
    if (i === 0) {
      prev = value;
      out.push(value);
    } else {
      const next = (value - prev) * multiplier + prev;
      out.push(next);
      prev = next;
    }
  }
  return out;
}

function rsi(values, period = 14) {
  if (values.length < period + 1) {
    return values.map(() => null);
  }

  const output = Array(values.length).fill(null);
  let avgGain = 0;
  let avgLoss = 0;

  for (let i = 1; i <= period; i += 1) {
    const diff = values[i] - values[i - 1];
    if (diff >= 0) {
      avgGain += diff;
    } else {
      avgLoss -= diff;
    }
  }

  avgGain /= period;
  avgLoss /= period;
  output[period] = 100 - 100 / (1 + avgGain / (avgLoss + 1e-9));

  for (let i = period + 1; i < values.length; i += 1) {
    const diff = values[i] - values[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    output[i] = 100 - 100 / (1 + avgGain / (avgLoss + 1e-9));
  }

  return output;
}

function formatDate(value) {
  const date = new Date(value);
  return `${date.getDate()}/${date.getMonth() + 1}`;
}

export default function IndicatorsChart({ historicalData }) {
  const data = useMemo(() => {
    if (!historicalData?.length) {
      return [];
    }

    const recent = historicalData.slice(-120);
    const closes = recent.map((item) => Number(item.close));
    const ema20 = ema(closes, 20);
    const rsi14 = rsi(closes, 14);

    return recent.map((item, idx) => ({
      date: item.date,
      close: closes[idx],
      sma20: sma(closes, 20, idx),
      ema20: ema20[idx],
      rsi14: rsi14[idx]
    }));
  }, [historicalData]);

  if (!data.length) {
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
      <h2>Technical Indicators</h2>
      <div className="chart-wrap indicators-main">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tickFormatter={formatDate} minTickGap={20} stroke="#475569" tick={axisStyle} />
            <YAxis domain={["auto", "auto"]} stroke="#475569" tick={axisStyle} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(label) => new Date(label).toDateString()} />
            <Line type="monotone" dataKey="close" stroke="#22d3ee" strokeWidth={2} dot={false} name="Close" />
            <Line type="monotone" dataKey="sma20" stroke="#38bdf8" strokeWidth={2} dot={false} name="SMA 20" />
            <Line type="monotone" dataKey="ema20" stroke="#a78bfa" strokeWidth={2} dot={false} name="EMA 20" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-wrap indicators-rsi">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tickFormatter={formatDate} minTickGap={20} stroke="#475569" tick={axisStyle} />
            <YAxis domain={[0, 100]} stroke="#475569" tick={axisStyle} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(label) => new Date(label).toDateString()} />
            <Line type="monotone" dataKey="rsi14" stroke="#fb7185" strokeWidth={2.2} dot={false} name="RSI 14" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
