import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/utils";
import type { SourceAttribution } from "@/types/report";

const SOURCE_TYPE_STYLE: Record<SourceAttribution["type"], string> = {
  market_api: "text-signal-blue bg-signal-blue-dim",
  news_api: "text-signal-amber bg-signal-amber-dim",
  vector_db: "text-ai bg-ai-dim",
  filing: "text-ai bg-ai-dim",
};

const SOURCE_TYPE_LABEL: Record<SourceAttribution["type"], string> = {
  market_api: "Market",
  news_api: "News",
  vector_db: "Filing",
  filing: "Filing",
};

interface SourceCardProps {
  source: SourceAttribution;
  compact?: boolean;
  className?: string;
}

export function SourceCard({ source, compact = false, className }: SourceCardProps) {
  if (compact) {
    return (
      
        href={source.url ?? undefined}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-mono",
          "text-ink-muted hover:text-ai border border-border hover:border-ai/30 bg-surface transition-colors",
          !source.url && "pointer-events-none",
          className
        )}
      >
        [{source.name}]
        {source.url && <ExternalLink className="w-2.5 h-2.5 opacity-60" />}
      </a>
    );
  }

  return (
    <div
      className={cn(
        "flex items-start gap-2.5 p-2.5 rounded-lg border border-border bg-surface",
        "hover:border-border-strong transition-colors",
        className
      )}
    >
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className={cn(
              "text-xs font-mono px-1.5 py-0.5 rounded border border-white/5",
              SOURCE_TYPE_STYLE[source.type]
            )}
          >
            {SOURCE_TYPE_LABEL[source.type]}
          </span>
          <span className="text-xs font-medium text-ink truncate">{source.name}</span>
        </div>
        <p className="text-xs text-ink-muted font-mono">
          {formatRelativeTime(source.fetched_at)}
        </p>
      </div>
      {source.url && (
        
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 p-1 rounded hover:bg-card text-ink-muted hover:text-ai transition-colors"
          aria-label={`Open ${source.name} in new tab`}
        >
          <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>
  );
}