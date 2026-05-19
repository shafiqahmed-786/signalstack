import { FileText, BarChart2 } from "lucide-react";
import { SourceCard } from "@/components/shared/SourceCard";
import { cn } from "@/lib/utils";
import { formatRelevanceScore } from "@/features/research/utils/formatters";
import type {
  FilingInsightsSection as FilingInsightsSectionType,
  SourceAttribution,
} from "@/types/report";

interface Props {
  section: FilingInsightsSectionType;
  sources: SourceAttribution[];
}

export function FilingInsightsSection({ section, sources }: Props) {
  const { content } = section;
  const sectionSources = sources.filter((s) => section.source_ids.includes(s.id));

  return (
    <div className="space-y-4">
      {/* Semantic query used */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface border border-border">
        <FileText className="w-3.5 h-3.5 text-ai shrink-0" aria-hidden="true" />
        <span className="text-xs text-ink-muted font-mono">Searched: </span>
        <span className="text-xs text-ai font-mono">"{content.query_used}"</span>
      </div>

      {/* Chunks */}
      {content.results.length === 0 ? (
        <p className="text-sm text-ink-muted text-center py-6">
          No highly relevant filing sections found for this query.
        </p>
      ) : (
        <div className="space-y-3">
          {content.results.map((result, i) => (
            <div
              key={i}
              className="p-4 rounded-xl border border-border bg-surface hover:border-border-strong transition-colors space-y-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-1.5 py-0.5 rounded text-xs font-mono bg-ai-dim text-ai border border-ai/20">
                    {result.document_type}
                  </span>
                  <span className="text-xs font-medium text-ink">
                    {result.document_title}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <BarChart2 className="w-3 h-3 text-ink-muted" aria-hidden="true" />
                  <span className={cn(
                    "text-xs font-mono",
                    result.relevance_score >= 0.8 ? "text-signal-green" :
                    result.relevance_score >= 0.65 ? "text-signal-amber" :
                    "text-ink-muted"
                  )}>
                    {formatRelevanceScore(result.relevance_score)}
                  </span>
                </div>
              </div>
              <blockquote className="border-l-2 border-ai/30 pl-3">
                <p className="text-xs text-ink-secondary leading-relaxed italic">
                  {result.text}
                </p>
              </blockquote>
            </div>
          ))}
        </div>
      )}

      {/* Sources */}
      {sectionSources.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-border">
          {sectionSources.map((s) => (
            <SourceCard key={s.id} source={s} compact />
          ))}
        </div>
      )}
    </div>
  );
}