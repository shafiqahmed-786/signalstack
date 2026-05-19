"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, LabelList,
} from "recharts";
import { cn } from "@/lib/utils";
import { TOOL_LABELS } from "@/features/research/types";
import type { ToolName } from "@/types/api";

const BAR_COLORS: Record<ToolName, string> = {
  market_data:        "#3b82f6",
  news_search:        "#f59e0b",
  vector_retrieval:   "#0fd4b0",
  sentiment_analysis: "#a855f7",
};

interface ChartEntry {
  tool: ToolName;
  durationMs: number;
  label: string;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ChartEntry }[] }) {
  if (!active || !payload?.length) return null;
  const { tool, durationMs } = payload[0].payload;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-xs font-mono shadow-xl">
      <p className="text-ink-secondary mb-0.5">{TOOL_LABELS[tool] ?? tool}</p>
      <p className="text-ink font-semibold">
        {durationMs >= 1000 ? `${(durationMs / 1000).toFixed(2)}s` : `${durationMs}ms`}
      </p>
    </div>
  );
}

interface ToolLatencyChartProps {
  data: Partial<Record<ToolName, number>>;
  height?: number;
  className?: string;
}

export function ToolLatencyChart({ data, height = 180, className }: ToolLatencyChartProps) {
  const chartData: ChartEntry[] = Object.entries(data)
    .filter((entry): entry is [ToolName, number] => entry[1] != null)
    .map(([tool, durationMs]) => ({
      tool: tool as ToolName,
      durationMs,
      label: TOOL_LABELS[tool as ToolName] ?? tool,
    }))
    .sort((a, b) => b.durationMs - a.durationMs);

  if (chartData.length === 0) {
    return (
      <div
        className={cn("flex items-center justify-center", className)}
        style={{ height }}
      >
        <p className="text-xs text-ink-muted font-mono">No latency data yet</p>
      </div>
    );
  }

  const fmt = (v: number) =>
    v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${v}ms`;

  return (
    <div className={className} aria-label="Tool latency chart">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ left: 8, right: 48, top: 4, bottom: 4 }}
        >
          <XAxis
            type="number"
            tickFormatter={fmt}
            tick={{ fontSize: 10, fill: "#4a5068", fontFamily: "var(--font-ibm-plex-mono)" }}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={96}
            tick={{ fontSize: 10, fill: "#8a93b2", fontFamily: "var(--font-ibm-plex-mono)" }}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar dataKey="durationMs" radius={[0, 4, 4, 0]} maxBarSize={24}>
            {chartData.map((entry) => (
              <Cell
                key={entry.tool}
                fill={BAR_COLORS[entry.tool] ?? "#8a93b2"}
                fillOpacity={0.85}
              />
            ))}
            <LabelList
              dataKey="durationMs"
              position="right"
              formatter={fmt}
              style={{
                fontSize: 10,
                fill: "#8a93b2",
                fontFamily: "var(--font-ibm-plex-mono)",
              }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}