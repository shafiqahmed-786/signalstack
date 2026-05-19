"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { CompanyCard } from "./CompanyCard";
import { PriceChart } from "./PriceChart";
import { OverviewSection } from "./sections/OverviewSection";
import { NewsSection } from "./sections/NewsSection";
import { ComparisonSection } from "./sections/ComparisonSection";
import { RiskSection } from "./sections/RiskSection";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatDuration, formatRelativeTime, cn } from "@/lib/utils";
import type { ResearchReport, ReportSection } from "@/types/report";
import type { ReportStatus } from "@/types/api";

interface ReportViewerProps {
  report: ResearchReport;
  status: ReportStatus;
  processingTimeMs: number | null;
  createdAt: string;
}

function SectionRenderer({ section, sources }: { section: ReportSection; sources: ResearchReport["sources"] }) {
  const [expanded, setExpanded] = useState(true);

  const sectionTitle = section.title;
  const isEmpty = !section;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden animate-slide-up">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface/30 transition-colors"
      >
        <h3 className="text-sm font-semibold text-ink">{sectionTitle}</h3>
        <ChevronDown className={cn("w-4 h-4 text-ink-muted transition-transform", expanded && "rotate-180")} />
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-border pt-4">
          {section.type === "overview" && <OverviewSection section={section} sources={sources} />}
          {section.type === "news" && <NewsSection section={section} sources={sources} />}
          {section.type === "comparison" && <ComparisonSection section={section} sources={sources} />}
          {section.type === "risk" && <RiskSection section={section} />}
          {section.type === "earnings" && (
            <div className="space-y-3">
              <p className="text-sm text-ink leading-relaxed">{section.content.narrative}</p>
              {section.content.filing_excerpts.map((e, i) => (
                <blockquote key={i} className="border-l-2 border-ai pl-3 py-1">
                  <p className="text-xs text-ink-secondary italic leading-relaxed">{e.text}</p>
                  <cite className="text-xs text-ink-muted font-mono mt-1 block not-italic">{e.document_title}</cite>
                </blockquote>
              ))}
            </div>
          )}
          {section.type === "filing_insights" && (
            <div className="space-y-3">
              <p className="text-xs text-ink-muted font-mono">Query: {section.content.query_used}</p>
              {section.content.results.map((r, i) => (
                <div key={i} className="p-3 rounded-lg bg-surface border border-border space-y-1">
                  <p className="text-xs text-ink leading-relaxed">{r.text}</p>
                  <p className="text-xs text-ink-muted font-mono">{r.document_title} · {(r.relevance_score * 100).toFixed(0)}% relevance</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ReportViewer({ report, status, processingTimeMs, createdAt }: ReportViewerProps) {
  return (
    <div className="space-y-6">
      {/* Report metadata */}
      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={status} />
        <span className="text-xs text-ink-muted font-mono">{formatRelativeTime(createdAt)}</span>
        {processingTimeMs && (
          <span className="text-xs text-ink-muted font-mono">· {formatDuration(processingTimeMs)}</span>
        )}
        {report.data_gaps.length > 0 && (
          <span className="text-xs text-signal-amber font-mono">
            · {report.data_gaps.length} data gap{report.data_gaps.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Executive summary */}
      <div className="rounded-xl border border-ai/20 bg-ai-glow p-5">
        <h3 className="text-xs font-mono text-ai uppercase tracking-wider mb-3">Executive Summary</h3>
        <p className="text-sm text-ink leading-relaxed">{report.executive_summary}</p>
      </div>

      {/* Company snapshots */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {report.companies.map((company) => (
          <div key={company.ticker} className="space-y-2">
            <CompanyCard company={company} />
            {company.price_history.length > 0 && (
              <div className="rounded-xl border border-border bg-card px-3 pt-2 pb-1">
                <p className="text-xs text-ink-muted font-mono mb-1">30-day price</p>
                <PriceChart data={company.price_history} ticker={company.ticker} />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Report sections */}
      <div className="space-y-4">
        {report.sections.map((section) => (
          <SectionRenderer key={section.id} section={section} sources={report.sources} />
        ))}
      </div>
    </div>
  );
}