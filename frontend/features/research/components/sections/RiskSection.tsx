import { AlertTriangle, Shield, AlertCircle } from "lucide-react";
import { getRiskSeverityDisplay } from "@/features/research/utils/confidence";
import { cn } from "@/lib/utils";
import type { RiskSection as RiskSectionType } from "@/types/report";

interface Props {
  section: RiskSectionType;
}

const SEVERITY_ICON = {
  high: AlertTriangle,
  medium: AlertCircle,
  low: Shield,
};

export function RiskSection({ section }: Props) {
  const { content } = section;
  const overallDisplay = getRiskSeverityDisplay(content.overall_level);

  return (
    <div className="space-y-4">
      {/* Overall risk level */}
      <div className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg border",
        content.overall_level === "high" ? "bg-signal-red-dim border-signal-red/20" :
        content.overall_level === "medium" ? "bg-signal-amber-dim border-signal-amber/20" :
        "bg-signal-green-dim border-signal-green/20"
      )}>
        <span className={cn("text-sm font-medium", overallDisplay.color)}>
          Overall: {content.overall_level.charAt(0).toUpperCase() + content.overall_level.slice(1)} Risk
        </span>
      </div>

      <p className="text-sm text-ink leading-relaxed">{content.summary}</p>

      {/* Risk factors */}
      <div className="space-y-2.5">
        {content.factors.map((factor, i) => {
          const display = getRiskSeverityDisplay(factor.severity);
          const Icon = SEVERITY_ICON[factor.severity];
          return (
            <div
              key={i}
              className="flex gap-3 p-3 rounded-lg border border-border hover:bg-surface/50 transition-colors"
            >
              <div className="mt-0.5 shrink-0">
                <Icon className={cn("w-4 h-4", display.color)} />
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-ink">{factor.title}</span>
                  <span className={cn("text-xs font-mono px-1.5 py-0.5 rounded border border-white/10", display.color)}>
                    {factor.category}
                  </span>
                </div>
                <p className="text-xs text-ink-secondary leading-relaxed">{factor.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}