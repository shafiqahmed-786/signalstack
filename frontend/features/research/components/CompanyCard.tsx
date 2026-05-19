import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import { SentimentBadge } from "@/components/shared/SentimentBadge";
import type { CompanySnapshot } from "@/types/report";

interface CompanyCardProps {
  company: CompanySnapshot;
  className?: string;
}

export function CompanyCard({ company, className }: CompanyCardProps) {
  const { metrics } = company;
  const changePositive = (metrics.change_1d_pct ?? 0) >= 0;

  return (
    <div className={cn("rounded-xl border border-border bg-card p-4 space-y-3", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono font-bold text-ai">{company.ticker}</span>
            {company.exchange && (
              <span className="text-xs text-ink-muted font-mono">{company.exchange}</span>
            )}
          </div>
          <p className="text-xs text-ink-secondary mt-0.5 leading-snug">{company.name}</p>
        </div>
        {company.news_sentiment && (
          <SentimentBadge
            sentiment={company.news_sentiment.overall}
            score={company.news_sentiment.score}
          />
        )}
      </div>

      {/* Price block */}
      {metrics.current_price !== null && (
        <div className="flex items-baseline gap-2">
          <span className="text-xl font-mono font-semibold text-ink">
            {formatCurrency(metrics.current_price)}
          </span>
          {metrics.change_1d_pct !== null && (
            <span className={cn(
              "text-sm font-mono",
              changePositive ? "text-signal-green" : "text-signal-red"
            )}>
              {formatPercent(metrics.change_1d_pct, true)}
            </span>
          )}
        </div>
      )}

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 gap-y-1.5 gap-x-4">
        {[
          { label: "Mkt Cap", value: formatCurrency(metrics.market_cap, true) },
          { label: "P/E", value: metrics.pe_ratio !== null ? `${metrics.pe_ratio.toFixed(1)}x` : "—" },
          { label: "Revenue", value: formatCurrency(metrics.revenue_ttm, true) },
          { label: "EPS", value: metrics.eps !== null ? formatCurrency(metrics.eps) : "—" },
        ].map(({ label, value }) => (
          <div key={label}>
            <dt className="text-xs text-ink-muted font-mono">{label}</dt>
            <dd className="text-xs text-ink font-mono mt-0.5">{value}</dd>
          </div>
        ))}
      </div>

      {company.sector && (
        <div className="pt-1 border-t border-border">
          <span className="text-xs text-ink-muted">{company.sector}</span>
        </div>
      )}
    </div>
  );
}