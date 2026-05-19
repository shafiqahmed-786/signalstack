import { SourceCard } from "@/components/shared/SourceCard";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/utils";
import {
  formatEarningsBeat,
  formatYoYGrowth,
  formatRelevanceScore,
} from "@/features/research/utils/formatters";
import type { EarningsSection as EarningsSectionType, SourceAttribution } from "@/types/report";

interface Props {
  section: EarningsSectionType;
  sources: SourceAttribution[];
}

export function EarningsSection({ section, sources }: Props) {
  const { content } = section;
  const sectionSources = sources.filter((s) => section.source_ids.includes(s.id));
  const epsBeat = formatEarningsBeat(content.highlights.eps?.beat_miss ?? null);

  return (
    <div className="space-y-4">
      {/* Period label */}
      <div className="flex items-center gap-2">
        <span className="px-2 py-0.5 rounded-md text-xs font-mono bg-ai-dim text-ai border border-ai/20">
          {content.ticker}
        </span>
        <span className="text-xs text-ink-muted font-mono">{content.period}</span>
      </div>

      {/* Metric highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {content.highlights.revenue && (
          <div className="p-3 rounded-lg bg-surface border border-border space-y-1">
            <p className="text-xs text-ink-muted font-mono">Revenue</p>
            <p className="text-sm font-mono font-semibold text-ink">
              {formatCurrency(content.highlights.revenue.actual, true)}
            </p>
            <p className={cn(
              "text-xs font-mono",
              content.highlights.revenue.yoy_growth_pct >= 0
                ? "text-signal-green"
                : "text-signal-red"
            )}>
              {formatYoYGrowth(content.highlights.revenue.yoy_growth_pct)}
            </p>
          </div>
        )}
        {content.highlights.eps && (
          <div className="p-3 rounded-lg bg-surface border border-border space-y-1">
            <p className="text-xs text-ink-muted font-mono">EPS</p>
            <p className="text-sm font-mono font-semibold text-ink">
              {formatCurrency(content.highlights.eps.actual)}
            </p>
            <p className={cn("text-xs font-mono", epsBeat.color)}>{epsBeat.label}</p>
          </div>
        )}
        {content.highlights.guidance && (
          <div className="p-3 rounded-lg bg-surface border border-border space-y-1">
            <p className="text-xs text-ink-muted font-mono">Guidance</p>
            <p className="text-xs text-ink leading-relaxed line-clamp-3">
              {content.highlights.guidance}
            </p>
          </div>
        )}
      </div>

      {/* Narrative */}
      <p className="text-sm text-ink leading-relaxed">{content.narrative}</p>

      {/* Filing excerpts */}
      {content.filing_excerpts.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono text-ink-muted uppercase tracking-wider">
            From Filings
          </h4>
          {content.filing_excerpts.map((excerpt, i) => (
            <blockquote key={i} className="border-l-2 border-ai/40 pl-3 py-1 space-y-1">
              <p className="text-xs text-ink-secondary italic leading-relaxed">
                {excerpt.text}
              </p>
              <cite className="text-xs text-ink-muted font-mono not-italic flex items-center gap-2">
                {excerpt.document_title}
                <span className="text-ai">{formatRelevanceScore(excerpt.relevance_score)}</span>
              </cite>
            </blockquote>
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