"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DataGap } from "@/types/report";

interface PartialFailureBannerProps {
  dataGaps: DataGap[];
  className?: string;
}

export function PartialFailureBanner({ dataGaps, className }: PartialFailureBannerProps) {
  const [expanded, setExpanded] = useState(false);

  if (dataGaps.length === 0) return null;

  const errors   = dataGaps.filter((g) => g.severity === "error");
  const warnings = dataGaps.filter((g) => g.severity === "warning");

  const summaryParts: string[] = [];
  if (errors.length)   summaryParts.push(`${errors.length} section${errors.length !== 1 ? "s" : ""} omitted`);
  if (warnings.length) summaryParts.push(`${warnings.length} warning${warnings.length !== 1 ? "s" : ""}`);

  return (
    <div
      className={cn(
        "rounded-xl border border-signal-amber/30 bg-signal-amber-dim overflow-hidden",
        className
      )}
      role="region"
      aria-label="Data gaps detected"
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-signal-amber/10 transition-colors text-left"
        aria-expanded={expanded}
        aria-controls="partial-failure-details"
      >
        <AlertTriangle className="w-4 h-4 text-signal-amber shrink-0" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-signal-amber">
            Partial data — {dataGaps.length} gap{dataGaps.length !== 1 ? "s" : ""} detected
          </p>
          {summaryParts.length > 0 && (
            <p className="text-xs text-ink-muted mt-0.5">{summaryParts.join(" · ")}</p>
          )}
        </div>
        {expanded
          ? <ChevronUp  className="w-4 h-4 text-ink-muted shrink-0" />
          : <ChevronDown className="w-4 h-4 text-ink-muted shrink-0" />
        }
      </button>

      {expanded && (
        <div
          id="partial-failure-details"
          className="px-4 pb-3 space-y-2 border-t border-signal-amber/20"
        >
          {dataGaps.map((gap, i) => (
            <div key={i} className="flex items-start gap-2 text-xs mt-2">
              <span
                className={cn(
                  "mt-1 w-1.5 h-1.5 rounded-full shrink-0",
                  gap.severity === "error" ? "bg-signal-red" : "bg-signal-amber"
                )}
                aria-hidden="true"
              />
              <span className="text-ink-secondary leading-relaxed">
                {gap.section_type && (
                  <span className="font-mono text-ink-muted mr-1">[{gap.section_type}]</span>
                )}
                {gap.reason}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}