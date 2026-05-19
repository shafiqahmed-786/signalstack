import Link from "next/link";
import { Pin, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { TickerChip } from "./TickerChip";
import { formatRelativeTime, truncate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ReportSummary } from "@/types/api";

interface ReportCardProps {
  report: ReportSummary;
  className?: string;
}

export function ReportCard({ report, className }: ReportCardProps) {
  const isProcessing = ["created", "planning", "dispatching", "synthesizing"].includes(report.status);

  return (
    <Link
      href={`/research/${report.id}`}
      className={cn(
        "group block rounded-xl border border-border bg-card p-4 hover:border-border-strong hover:bg-card-hover transition-all",
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0 space-y-2">
          {/* Query */}
          <p className="text-sm font-medium text-ink group-hover:text-ai transition-colors leading-snug">
            {truncate(report.query, 100)}
          </p>

          {/* Tickers */}
          {report.companies.length > 0 && (
            <div className="flex gap-1.5 flex-wrap">
              {report.companies.slice(0, 5).map((t) => (
                <TickerChip key={t} ticker={t} />
              ))}
            </div>
          )}

          {/* Meta row */}
          <div className="flex items-center gap-3 flex-wrap">
            <StatusBadge status={report.status} />
            <span className="text-xs text-ink-muted font-mono">{formatRelativeTime(report.created_at)}</span>
            {report.cache_hit && (
              <span className="text-xs text-ink-muted font-mono">⚡ cached</span>
            )}
            {report.tags.map((tag) => (
              <span key={tag} className="text-xs text-ink-muted font-mono">#{tag}</span>
            ))}
          </div>
        </div>

        {/* Right side */}
        <div className="flex flex-col items-end gap-2 shrink-0">
          {report.is_pinned && <Pin className="w-3.5 h-3.5 text-signal-amber" />}
          {isProcessing && <Loader2 className="w-3.5 h-3.5 text-ai animate-spin" />}
          {report.status === "completed" && <CheckCircle2 className="w-3.5 h-3.5 text-signal-green" />}
          {report.status === "failed" && <XCircle className="w-3.5 h-3.5 text-signal-red" />}
        </div>
      </div>
    </Link>
  );
}