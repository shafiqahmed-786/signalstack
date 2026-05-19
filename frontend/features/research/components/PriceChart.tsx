"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { formatCurrency } from "@/lib/utils";
import type { PricePoint } from "@/types/report";

interface PriceChartProps {
  data: PricePoint[];
  ticker: string;
  color?: string;
  height?: number;
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg px-2.5 py-1.5 text-xs font-mono shadow-xl">
      <p className="text-ink-muted">{label}</p>
      <p className="text-ai font-semibold">{formatCurrency(payload[0].value)}</p>
    </div>
  );
}

export function PriceChart({ data, ticker, color = "#0fd4b0", height = 120 }: PriceChartProps) {
  if (!data.length) return null;

  const firstPrice = data[0]?.close ?? 0;
  const lastPrice = data[data.length - 1]?.close ?? 0;
  const isPositive = lastPrice >= firstPrice;

  const chartColor = isPositive ? "#22c55e" : "#ef4444";

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="date"
            hide
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis
            hide
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={firstPrice} stroke="rgba(255,255,255,0.1)" strokeDasharray="3 3" />
          <Line
            type="monotone"
            dataKey="close"
            stroke={chartColor}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: chartColor }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}