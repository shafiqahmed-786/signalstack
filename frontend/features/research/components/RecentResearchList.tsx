"use client";

import Link from "next/link";
import { ArrowRight, Search } from "lucide-react";
import { ReportCard } from "./ReportCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { useDashboardMetrics } from "@/features/research/hooks/useDashboardMetrics";

interface RecentResearchListProps {
  limit?: number;
  showViewAll?: boolean;
}

export function RecentResearchList({
  limit = 5,
  showViewAll = true,
}: RecentResearchListProps) {
  const { recentActivity, isLoading } = useDashboardMetrics();
  const reports = recentActivity.slice(0, limit);

  return (
    <section aria-label="Recent research">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-ink">Recent Research</h2>
        {showViewAll && (
          <Link
            href="/history"
            className="flex items-center gap-1 text-xs text-ai hover:text-ai/80 transition-colors font-mono"
          >
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-2" aria-busy="true">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 rounded-xl bg-card border border-border animate-pulse"
            />
          ))}
        </div>
      ) : reports.length > 0 ? (
        <div className="space-y-2">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Search className="w-5 h-5" />}
          title="No research yet"
          description="Submit your first query to get AI-powered insights"
          action={
            <Link
              href="/research"
              className="text-xs text-ai border border-ai/30 px-3 py-1.5 rounded-md hover:bg-ai-dim transition-colors"
            >
              Start researching
            </Link>
          }
        />
      )}
    </section>
  );
}