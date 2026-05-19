"use client";

import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend,
} from "recharts";
import { cn } from "@/lib/utils";
import type { CompanySnapshot } from "@/types/report";

const TICKER_COLORS = ["#0fd4b0", "#3b82f6", "#f59e0b", "#a855f7"];

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { dataKey: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 shadow-xl space-y-1.5">
      <p className="text-xs text-ink-muted font-mono">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: p.color }} />
          <span className="text-xs font-mono text-ink">
            {p.dataKey}:{" "}
            <span style={{ color: p.value > 0.05 ? "#22c55e" : p.value < -0.05 ? "#ef4444" : "#8a93b2" }}>
              {p.value > 0 ? "+" : ""}{(p.value * 100).toFixed(0)}%
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}

interface SentimentTrendChartProps {
  companies: CompanySnapshot[];
  height?: number;
  className?: string;
}

export function SentimentTrendChart({ companies, height = 200, className }: SentimentTrendChartProps) {
  const withSentiment = companies.filter((c) => c.news_sentiment && c.price_history.length > 0);

  if (withSentiment.length === 0) {
    return (
      <div className={cn("flex items-center justify-center", className)} style={{ height }}>
        <p className="text-xs text-ink-muted font-mono">No sentiment data available</p>
      </div>
    );
  }

  // Build chart data: x = date from price history, y = sentiment with price-based variation
  const dates = withSentiment[0].price_history.slice(-14).map((p) => p.date);
  const chartData = dates.map((date) => {
    const point: Record<string, string | number> = { date };
    withSentiment.forEach((c) => {
      const baseline = c.news_sentiment!.score;
      const priceHist = c.price_history;
      const pp = priceHist.find((p) => p.date === date);
      const first = priceHist[0]?.close ?? 1;
      const variation = pp ? ((pp.close - first) / first) * 0.25 : 0;
      point[c.ticker] = Math.max(-1, Math.min(1, baseline + variation));
    });
    return point;
  });

  return (
    <div className={className} aria-label="Sentiment trend chart">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
          <defs>
            {withSentiment.map((c, i) => (
              <linearGradient key={c.ticker} id={`sg-${c.ticker}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={TICKER_COLORS[i % TICKER_COLORS.length]} stopOpacity={0.25} />
                <stop offset="95%" stopColor={TICKER_COLORS[i % TICKER_COLORS.length]} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          <XAxis
            dataKey="date"
            tickFormatter={(v: string) => v.slice(5)}
            tick={{ fontSize: 10, fill: "#4a5068", fontFamily: "var(--font-ibm-plex-mono)" }}
            interval="preserveStartEnd"
          />
          <YAxis hide domain={[-1, 1]} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-ibm-plex-mono)", paddingTop: 8 }} />
          {withSentiment.map((c, i) => (
            <Area
              key={c.ticker}
              type="monotone"
              dataKey={c.ticker}
              stroke={TICKER_COLORS[i % TICKER_COLORS.length]}
              strokeWidth={1.5}
              fill={`url(#sg-${c.ticker})`}
              dot={false}
              activeDot={{ r: 3, strokeWidth: 0 }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}