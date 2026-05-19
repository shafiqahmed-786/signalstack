"use client";

import { QueryInput } from "@/features/research/components/QueryInput";
import { OrchestrationStream } from "@/features/research/components/OrchestrationStream";
import { useResearchStream } from "@/features/research/hooks/useResearchStream";

export default function ResearchPage() {
  const { submitQuery, cancelStream, orchestration, isStreaming } = useResearchStream();

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-ink">Research</h1>
        <p className="text-sm text-ink-secondary mt-1">
          Ask anything about markets, companies, or financials.
        </p>
      </div>

      {/* Query input */}
      <QueryInput
        onSubmit={submitQuery}
        isLoading={isStreaming}
        onCancel={cancelStream}
      />

      {/* Streaming orchestration view */}
      {orchestration.phase !== "idle" && (
        <OrchestrationStream state={orchestration} />
      )}

      {/* Hint when idle */}
      {orchestration.phase === "idle" && (
        <div className="rounded-xl border border-border bg-card/50 p-5">
          <h3 className="text-xs font-mono text-ink-muted uppercase tracking-wider mb-3">
            How it works
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { step: "01", title: "Query Planning", desc: "AI analyses your question and selects the right data tools" },
              { step: "02", title: "Data Gathering", desc: "Market data, news, and filings retrieved in parallel" },
              { step: "03", title: "Report Synthesis", desc: "Claude synthesises data into a structured, cited report" },
            ].map(({ step, title, desc }) => (
              <div key={step} className="space-y-1.5">
                <span className="text-xs font-mono text-ai">{step}</span>
                <p className="text-sm font-medium text-ink">{title}</p>
                <p className="text-xs text-ink-muted leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}