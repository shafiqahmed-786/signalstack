"use client";

import { useState, useRef, useCallback } from "react";
import { Search, Loader2, X } from "lucide-react";
import { TickerChip } from "./TickerChip";
import { QUERY_SUGGESTIONS } from "../types";
import { cn } from "@/lib/utils";

interface QueryInputProps {
  onSubmit: (query: string, companies?: string[]) => void;
  isLoading?: boolean;
  onCancel?: () => void;
  className?: string;
}

const TICKER_REGEX = /\b([A-Z]{1,5})\b/g;

function extractTickers(text: string): string[] {
  const matches = [...text.matchAll(TICKER_REGEX)];
  const known = new Set(["NVDA", "AMD", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "NFLX", "JPM", "GS"]);
  return [...new Set(matches.map((m) => m[1]).filter((t) => known.has(t)))];
}

export function QueryInput({ onSubmit, isLoading, onCancel, className }: QueryInputProps) {
  const [query, setQuery] = useState("");
  const [companies, setCompanies] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleQueryChange = useCallback((value: string) => {
    setQuery(value);
    const tickers = extractTickers(value);
    setCompanies(tickers);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!query.trim() || isLoading) return;
    onSubmit(query.trim(), companies.length ? companies : undefined);
    setShowSuggestions(false);
  }, [query, companies, isLoading, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const applySuggestion = (suggestion: typeof QUERY_SUGGESTIONS[0]) => {
    setQuery(suggestion.query);
    setCompanies(suggestion.tickers ?? []);
    setShowSuggestions(false);
    textareaRef.current?.focus();
  };

  return (
    <div className={cn("w-full space-y-3", className)}>
      {/* Main input area */}
      <div className="relative rounded-xl border border-border-strong bg-card focus-within:border-ai/50 transition-colors">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => !query && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          placeholder="Ask anything about a company or market… e.g. &quot;Analyse NVIDIA Q3 earnings vs AMD&quot;"
          rows={3}
          className="w-full bg-transparent px-4 pt-4 pb-12 text-sm text-ink placeholder:text-ink-muted resize-none focus:outline-none font-sans leading-relaxed"
          disabled={isLoading}
        />

        {/* Detected tickers */}
        {companies.length > 0 && (
          <div className="absolute left-4 bottom-12 flex gap-1.5 flex-wrap">
            {companies.map((t) => (
              <TickerChip
                key={t}
                ticker={t}
                onRemove={() => setCompanies((prev) => prev.filter((x) => x !== t))}
              />
            ))}
          </div>
        )}

        {/* Footer row */}
        <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-4 pb-3">
          <span className="text-xs text-ink-muted font-mono">⌘ + Enter to submit</span>
          <div className="flex items-center gap-2">
            {isLoading && onCancel && (
              <button
                onClick={onCancel}
                className="flex items-center gap-1 text-xs text-ink-secondary hover:text-signal-red transition-colors"
              >
                <X className="w-3 h-3" /> Cancel
              </button>
            )}
            <button
              onClick={handleSubmit}
              disabled={!query.trim() || isLoading}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                "bg-ai text-base hover:bg-ai/90 disabled:opacity-40 disabled:cursor-not-allowed"
              )}
            >
              {isLoading ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Search className="w-3 h-3" />
              )}
              {isLoading ? "Researching…" : "Research"}
            </button>
          </div>
        </div>
      </div>

      {/* Suggestions */}
      {showSuggestions && !isLoading && (
        <div className="rounded-xl border border-border bg-card p-2 animate-slide-up">
          <p className="px-2 py-1 text-xs text-ink-muted font-mono mb-1">Suggestions</p>
          <div className="space-y-0.5">
            {QUERY_SUGGESTIONS.map((s) => (
              <button
                key={s.label}
                onMouseDown={() => applySuggestion(s)}
                className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-surface transition-colors group"
              >
                <div className="text-ink group-hover:text-ai transition-colors">{s.label}</div>
                <div className="text-ink-muted mt-0.5 leading-relaxed truncate">{s.query}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}