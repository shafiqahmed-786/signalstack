"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Plus, History, Home, FileText, X } from "lucide-react";
import { cn, truncate } from "@/lib/utils";
import { useReports } from "@/features/research/hooks/useReports";

/**
 * Global command palette — mount once in the dashboard layout.
 * Registers cmd+k / ctrl+k to open automatically.
 */

interface Command {
  id: string;
  label: string;
  meta?: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
  kbd?: string;
}

export function CommandPalette() {
  const [open, setOpen]   = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const { data } = useReports({ page_size: 6 });

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setCursor(0);
  }, []);

  // Global toggle
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 30);
  }, [open]);

  const staticCmds: Command[] = useMemo(() => [
    {
      id: "new", label: "New Research", meta: "Start a query", icon: Plus,
      action: () => { router.push("/research"); close(); }, kbd: "⌘N",
    },
    {
      id: "history", label: "History", meta: "Browse saved reports", icon: History,
      action: () => { router.push("/history"); close(); },
    },
    {
      id: "home", label: "Dashboard", meta: "Go to home", icon: Home,
      action: () => { router.push("/"); close(); },
    },
  ], [router, close]);

  const reportCmds: Command[] = useMemo(() => {
    if (!data?.reports) return [];
    return data.reports
      .filter((r) => !query || r.query.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 4)
      .map((r) => ({
        id: `r-${r.id}`,
        label: truncate(r.query, 55),
        meta: r.status,
        icon: FileText,
        action: () => { router.push(`/research/${r.id}`); close(); },
      }));
  }, [data, query, router, close]);

  const commands = useMemo(() => {
    const q = query.toLowerCase();
    const filtered = staticCmds.filter(
      (c) => !q || c.label.toLowerCase().includes(q) || (c.meta ?? "").toLowerCase().includes(q)
    );
    return [...filtered, ...reportCmds];
  }, [query, staticCmds, reportCmds]);

  // Keyboard navigation within palette
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") { e.preventDefault(); setCursor((i) => Math.min(i + 1, commands.length - 1)); }
      if (e.key === "ArrowUp")   { e.preventDefault(); setCursor((i) => Math.max(i - 1, 0)); }
      if (e.key === "Enter" && commands[cursor]) commands[cursor].action();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, commands, cursor]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 animate-fade-in" onClick={close} aria-hidden="true" />
      <div role="dialog" aria-label="Command palette" aria-modal="true" className="fixed top-[18vh] left-1/2 -translate-x-1/2 w-full max-w-lg z-50 px-4 animate-slide-up">
        <div className="rounded-2xl border border-border-strong bg-card shadow-2xl overflow-hidden">

          {/* Input */}
          <div className="flex items-center gap-3 px-4 py-3.5 border-b border-border">
            <Search className="w-4 h-4 text-ink-muted shrink-0" aria-hidden="true" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => { setQuery(e.target.value); setCursor(0); }}
              placeholder="Search reports or run a command…"
              className="flex-1 bg-transparent text-sm text-ink placeholder:text-ink-muted focus:outline-none"
              aria-label="Command search"
            />
            <button onClick={close} className="p-0.5 rounded text-ink-muted hover:text-ink transition-colors" aria-label="Close">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Results */}
          <div role="listbox" className="py-1.5 max-h-72 overflow-y-auto">
            {commands.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-ink-muted">
                No results for "{query}"
              </p>
            ) : (
              commands.map((cmd, i) => {
                const Icon = cmd.icon;
                const active = i === cursor;
                return (
                  <div
                    key={cmd.id}
                    role="option"
                    aria-selected={active}
                    onClick={cmd.action}
                    onMouseEnter={() => setCursor(i)}
                    className={cn(
                      "flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors",
                      active ? "bg-ai-glow" : "hover:bg-surface"
                    )}
                  >
                    <div className={cn(
                      "w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border",
                      active ? "border-ai/30 bg-ai-dim text-ai" : "border-border bg-surface text-ink-muted"
                    )}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={cn("text-sm truncate", active ? "text-ai" : "text-ink")}>{cmd.label}</p>
                      {cmd.meta && <p className="text-xs text-ink-muted font-mono mt-0.5">{cmd.meta}</p>}
                    </div>
                    {cmd.kbd && <kbd className="text-xs text-ink-muted font-mono hidden sm:block">{cmd.kbd}</kbd>}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-border flex items-center gap-3 text-xs text-ink-muted font-mono">
            <span>↑↓ navigate</span>
            <span>↵ open</span>
            <span>esc close</span>
          </div>
        </div>
      </div>
    </>
  );
}