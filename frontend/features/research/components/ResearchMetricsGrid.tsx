"use client";

import { FileText, Clock, Zap, TrendingUp } from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";
import { useDashboardMetrics } from "@/features/research/hooks/useDashboardMetrics";

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  icon: React.ComponentType<{ className?: string }>;
  highlight?: boolean;
}

function MetricCard({ label, value, sub, icon: Icon, highlight }: MetricCardProps) {
  return (
    <div className="p-4 rounded-xl border border-border bg-card space-y-3">
      <div className={cn(
        "w-8 h-8 rounded-lg flex items-center justify-center border",
        highlight
          ? "bg-ai-dim border-ai/25 text-ai"
          : "bg-surface border-border text-ink-muted"
      )}>
        <Icon className="w-4 h-4" aria-hidden="true" />
      </div>
      <div>
        <p className="text-2xl font-mono font-semibold text-ink tracking-tight">{value}</p>
        <p className="text-xs text-ink-muted mt-0.5">{label}</p>
        {sub && <p className="text-xs text-ink-muted font-mono mt-1 opacity-70">{sub}</p>}
      </div>
    </div>
  );
}

export function ResearchMetricsGrid() {
  const {
    total, avgProcessingMs, cacheHitRate, successRate, isLoading,
  } = useDashboardMetrics();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" aria-busy="true">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-xl border border-border bg-card animate-pulse" />
        ))}
      </div>
    );
  }

  const cacheRatePct = cacheHitRate !== null
    ? `${(cacheHitRate * 100).toFixed(0)}%` : "—";
  const successRatePct = successRate !== null
    ? `${(successRate * 100).toFixed(0)}%` : "—";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <MetricCard
        label="Total Reports"
        value={total > 0 ? total.toLocaleString() : "0"}
        icon={FileText}
        highlight={total > 0}
      />
      <MetricCard
        label="Avg. Duration"
        value={formatDuration(avgProcessingMs)}
        sub="per research query"
        icon={Clock}
      />
      <MetricCard
        label="Cache Hit Rate"
        value={cacheRatePct}
        sub="instant responses"
        icon={Zap}
        highlight={(cacheHitRate ?? 0) > 0.25}
      />
      <MetricCard
        label="Success Rate"
        value={successRatePct}
        sub="completed queries"
        icon={TrendingUp}
        highlight={(successRate ?? 0) > 0.8}
      />
    </div>
  );
}