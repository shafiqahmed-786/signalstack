"use client";

import { useState } from "react";
import { Search, Filter } from "lucide-react";
import { useReports } from "@/features/research/hooks/useReports";
import { ReportCard } from "@/features/research/components/ReportCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";

const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Completed", value: "completed" },
  { label: "Partial", value: "partial" },
  { label: "Failed", value: "failed" },
  { label: "Processing", value: "synthesizing" },
];

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [pinned, setPinned] = useState(false);

  const { data, isLoading, error, refetch } = useReports({
    page,
    page_size: 20,
    status: statusFilter,
    pinned: pinned || undefined,
  });

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Research History</h1>
          <p className="text-sm text-ink-secondary mt-1">
            {data ? `${data.total} report${data.total !== 1 ? "s" : ""}` : "—"}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex gap-1 p-1 bg-surface rounded-lg border border-border">
          {STATUS_FILTERS.map((f) => (
            <button
              key={String(f.value)}
              onClick={() => { setStatusFilter(f.value); setPage(1); }}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                statusFilter === f.value
                  ? "bg-ai-dim text-ai border border-ai/25"
                  : "text-ink-secondary hover:text-ink"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => { setPinned(!pinned); setPage(1); }}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition-colors ${
            pinned ? "border-signal-amber/30 bg-signal-amber-dim text-signal-amber" : "border-border text-ink-secondary hover:text-ink"
          }`}
        >
          <Filter className="w-3 h-3" />
          Pinned
        </button>
      </div>

      {/* Content */}
      {error ? (
        <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-28 rounded-xl bg-card border border-border animate-pulse" />
          ))}
        </div>
      ) : data?.reports.length ? (
        <>
          <div className="space-y-2">
            {data.reports.map((r) => <ReportCard key={r.id} report={r} />)}
          </div>
          {/* Pagination */}
          {(data.has_next || page > 1) && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 text-xs border border-border rounded-lg text-ink-secondary disabled:opacity-40 hover:text-ink hover:border-border-strong transition-colors"
              >
                ← Prev
              </button>
              <span className="text-xs text-ink-muted font-mono">Page {page}</span>
              <button
                disabled={!data.has_next}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-xs border border-border rounded-lg text-ink-secondary disabled:opacity-40 hover:text-ink hover:border-border-strong transition-colors"
              >
                Next →
              </button>
            </div>
          )}
        </>
      ) : (
        <EmptyState
          icon={<Search className="w-5 h-5" />}
          title="No reports found"
          description={statusFilter ? `No ${statusFilter} reports yet` : "Submit your first research query to get started"}
        />
      )}
    </div>
  );
}