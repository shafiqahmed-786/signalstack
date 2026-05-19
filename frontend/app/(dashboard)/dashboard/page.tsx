"use client";

import Link from "next/link";
import { useUser } from "@clerk/nextjs";
import { Search, History, TrendingUp, ArrowRight } from "lucide-react";
import { useReports } from "@/features/research/hooks/useReports";
import { ReportCard } from "@/features/research/components/ReportCard";
import { EmptyState } from "@/components/shared/EmptyState";

export default function DashboardPage() {
  const { user } = useUser();
  const { data, isLoading } = useReports({ page_size: 5 });

  const firstName = user?.firstName ?? "Analyst";

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-10">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-semibold text-ink">
          Good {getTimeOfDay()}, {firstName}
        </h1>
        <p className="text-sm text-ink-secondary mt-1">
          Your AI-powered research workspace is ready.
        </p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { href: "/research", icon: Search, label: "New Research", desc: "Start a research query", accent: true },
          { href: "/history", icon: History, label: "Report History", desc: "View past analyses" },
          { href: "/research", icon: TrendingUp, label: "Market Overview", desc: "Quick market snapshot" },
        ].map(({ href, icon: Icon, label, desc, accent }) => (
          <Link
            key={href + label}
            href={href}
            className={`group flex items-center gap-3 p-4 rounded-xl border transition-all ${
              accent
                ? "border-ai/30 bg-ai-glow hover:bg-ai-dim"
                : "border-border bg-card hover:border-border-strong hover:bg-card-hover"
            }`}
          >
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
              accent ? "bg-ai-dim border border-ai/30" : "bg-surface border border-border"
            }`}>
              <Icon className={`w-4 h-4 ${accent ? "text-ai" : "text-ink-secondary"}`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${accent ? "text-ai" : "text-ink"}`}>{label}</p>
              <p className="text-xs text-ink-muted">{desc}</p>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-ink-muted opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
        ))}
      </div>

      {/* Recent reports */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">Recent Research</h2>
          <Link href="/history" className="text-xs text-ai hover:text-ai/80 transition-colors font-mono">
            View all →
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 rounded-xl bg-card border border-border animate-pulse" />
            ))}
          </div>
        ) : data?.reports.length ? (
          <div className="space-y-2">
            {data.reports.map((r) => <ReportCard key={r.id} report={r} />)}
          </div>
        ) : (
          <EmptyState
            icon={<Search className="w-5 h-5" />}
            title="No research yet"
            description="Submit your first query to get started"
            action={
              <Link href="/research" className="text-xs text-ai hover:text-ai/80 border border-ai/30 px-3 py-1.5 rounded-md transition-colors">
                Start research →
              </Link>
            }
          />
        )}
      </div>
    </div>
  );
}

function getTimeOfDay() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}