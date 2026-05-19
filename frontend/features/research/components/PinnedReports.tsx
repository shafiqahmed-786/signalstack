"use client";

import Link from "next/link";
import { Pin } from "lucide-react";
import { ReportCard } from "./ReportCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { useReports } from "@/features/research/hooks/useReports";

interface PinnedReportsProps {
  limit?: number;
}

export function PinnedReports({ limit = 3 }: PinnedReportsProps) {
  const { data, isLoading } = useReports({ pinned: true, page_size: limit });

  if (isLoading) {
    return (
      <section aria-label="Pinned reports" aria-busy="true">
        <div className="flex items-center gap-2 mb-3">
          <Pin className="w-3.5 h-3.5 text-signal-amber" />
          <h2 className="text-sm font-semibold text-ink">Pinned</h2>
        </div>
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-card border border-border animate-pulse" />
          ))}
        </div>
      </section>
    );
  }

  const reports = data?.reports ?? [];

  if (reports.length === 0) {
    return (
      <section aria-label="Pinned reports">
        <div className="flex items-center gap-2 mb-3">
          <Pin className="w-3.5 h-3.5 text-signal-amber" />
          <h2 className="text-sm font-semibold text-ink">Pinned</h2>
        </div>
        <EmptyState
          icon={<Pin className="w-4 h-4" />}
          title="No pinned reports"
          description="Pin important reports for quick access"
          className="py-8 border border-border rounded-xl bg-card/50"
        />
      </section>
    );
  }

  return (
    <section aria-label="Pinned reports">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Pin className="w-3.5 h-3.5 text-signal-amber" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-ink">Pinned</h2>
        </div>
        <span className="text-xs text-ink-muted font-mono">{reports.length}</span>
      </div>
      <div className="space-y-2">
        {reports.map((report) => (
          <ReportCard key={report.id} report={report} />
        ))}
      </div>
    </section>
  );
}