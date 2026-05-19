import { ExternalLink } from "lucide-react";
import { SentimentBadge } from "@/components/shared/SentimentBadge";
import { formatRelativeTime } from "@/lib/utils";
import type { NewsSection as NewsSectionType, SourceAttribution } from "@/types/report";

interface Props {
  section: NewsSectionType;
  sources: SourceAttribution[];
}

export function NewsSection({ section }: Props) {
  const allArticles = section.content.articles.flatMap((g) =>
    g.items.map((item) => ({ ...item, ticker: g.ticker }))
  );

  return (
    <div className="space-y-3">
      {allArticles.map((article) => (
        <div
          key={article.source_id + article.title}
          className="group flex gap-3 p-3 rounded-lg border border-border hover:border-border-strong hover:bg-surface/50 transition-all"
        >
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-start gap-2 flex-wrap">
              <span className="text-xs font-mono text-ai shrink-0">{article.ticker}</span>
              
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-ink group-hover:text-ai transition-colors leading-snug line-clamp-2 flex-1"
              >
                {article.title}
                <ExternalLink className="inline w-3 h-3 ml-1 opacity-0 group-hover:opacity-60 transition-opacity" />
              </a>
            </div>
            <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2">
              {article.summary}
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <SentimentBadge sentiment={article.sentiment} score={article.sentiment_score} />
              <span className="text-xs text-ink-muted font-mono">{article.source_name}</span>
              <span className="text-xs text-ink-muted font-mono">
                {formatRelativeTime(article.published_at)}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}