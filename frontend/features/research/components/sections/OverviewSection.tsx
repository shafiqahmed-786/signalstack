import { Sparkles } from "lucide-react";
import { SourceCard } from "@/components/shared/SourceCard";
import type { OverviewSection as OverviewSectionType, SourceAttribution } from "@/types/report";

interface Props {
  section: OverviewSectionType;
  sources: SourceAttribution[];
}

export function OverviewSection({ section, sources }: Props) {
  const sectionSources = sources.filter((s) =>
    section.source_ids.includes(s.id)
  );

  return (
    <div className="space-y-4">
      {/* Narrative */}
      <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">
        {section.content.narrative}
      </p>

      {/* Key highlights */}
      {section.content.key_highlights.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-mono text-ink-muted uppercase tracking-wider">
            Key Highlights
          </h4>
          <ul className="space-y-2" role="list">
            {section.content.key_highlights.map((highlight, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink">
                <Sparkles
                  className="w-3.5 h-3.5 text-ai mt-0.5 shrink-0"
                  aria-hidden="true"
                />
                <span>{highlight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Source attribution */}
      {sectionSources.length > 0 && (
        <div
          className="flex flex-wrap gap-1.5 pt-2 border-t border-border"
          aria-label="Sources"
        >
          {sectionSources.map((s) => (
            <SourceCard key={s.id} source={s} compact />
          ))}
        </div>
      )}
    </div>
  );
}