"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { cn, formatCurrency } from "@/lib/utils";
import type { ComparisonSection as ComparisonSectionType, SourceAttribution } from "@/types/report";

interface Props {
  section: ComparisonSectionType;
  sources: SourceAttribution[];
}

const TICKER_COLORS = ["#0fd4b0", "#3b82f6", "#f59e0b", "#a855f7", "#ec4899"];

export function ComparisonSection({ section }: Props) {
  const tickers = section.content.tickers;

  return (
    <div className="space-y-5">
      {/* AI Commentary */}
      <p className="text-sm text-ink leading-relaxed">{section.content.ai_commentary}</p>

      {/* Metrics table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left text-ink-muted py-2 pr-4 font-medium">Metric</th>
              {tickers.map((t, i) => (
                <th key={t} className="text-right py-2 px-3 font-medium" style={{ color: TICKER_COLORS[i % TICKER_COLORS.length] }}>
                  {t}
                </th>
              ))}
              <th className="text-right py-2 pl-3 text-ink-muted font-medium">Insight</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {section.content.metrics.map((metric) => (
              <tr key={metric.name} className="hover:bg-surface/50 transition-colors">
                <td className="py-2.5 pr-4 text-ink-secondary">{metric.name}</td>
                {metric.values.map((v, i) => (
                  <td
                    key={v.ticker}
                    className={cn(
                      "text-right py-2.5 px-3",
                      metric.winner === v.ticker ? "text-signal-green font-semibold" : "text-ink"
                    )}
                  >
                    {v.formatted}
                    {metric.winner === v.ticker && <span className="ml-1 text-signal-green">↑</span>}
                  </td>
                ))}
                <td className="text-right py-2.5 pl-3 text-ink-muted max-w-[200px] text-wrap">
                  {metric.insight}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Chart (first chart_data entry) */}
      {section.content.chart_data[0] && (
        <div className="mt-4">
          <p className="text-xs text-ink-muted font-mono mb-2">{section.content.chart_data[0].metric}</p>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={section.content.chart_data[0].data} margin={{ left: 0, right: 0 }}>
              <XAxis dataKey="ticker" tick={{ fontSize: 11, fill: "#8a93b2", fontFamily: "var(--font-ibm-plex-mono)" }} />
              <YAxis hide />
              <Tooltip
                formatter={(v: number) => [formatCurrency(v, true), section.content.chart_data[0].metric]}
                contentStyle={{ background: "#141c2e", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#8a93b2" }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {section.content.chart_data[0].data.map((_, i) => (
                  <Cell key={i} fill={TICKER_COLORS[i % TICKER_COLORS.length]} fillOpacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}