"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { Archive, ArrowLeft, Pin } from "lucide-react";

import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { StatusBadge } from "@/components/shared/StatusBadge";

import { ReportSkeleton } from "@/features/research/components/ReportSkeleton";
import { ReportViewer } from "@/features/research/components/ReportViewer";
import {
  useArchiveReport,
  useReport,
  useUpdateReport,
} from "@/features/research/hooks/useReports";

import { truncate } from "@/lib/utils";

interface Props {
  params: Promise<{ id: string }>;
}

const PROCESSING_STATES = new Set([
  "created",
  "queued",
  "planning",
  "fetching_data",
  "running_sentiment",
  "retrieving_context",
  "synthesizing",
  "validating",
  "saving",
]);

export default function ReportPage({ params }: Props) {
  const { id } = use(params);

  const router = useRouter();

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useReport(id);

  const updateMutation = useUpdateReport();

  const archiveMutation = useArchiveReport();

  const handleArchive = async () => {
    try {
      await archiveMutation.mutateAsync(id);

      router.push("/history");
    } catch (err) {
      console.error("Failed to archive report:", err);
    }
  };

  const handleTogglePin = async () => {
    if (!data) {
      return;
    }

    try {
      await updateMutation.mutateAsync({
        id,
        payload: {
          is_pinned: !data.is_pinned,
        },
      });
    } catch (err) {
      console.error("Failed to update report:", err);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="h-8 w-64 rounded-lg bg-card animate-pulse mb-8" />

        <ReportSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10">
        <ErrorState
          title="Unable to load report"
          message={(error as Error).message}
          onRetry={() => {
            void refetch();
          }}
        />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10">
        <EmptyState
          title="Report not found"
          description="The requested report could not be located."
        />
      </div>
    );
  }

  if (!data.report && data.status === "failed") {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10">
        <ErrorState
          title="Research failed"
          message={
            data.error_message ??
            "The research orchestration pipeline encountered an error."
          }
          onRetry={() => {
            router.push("/research");
          }}
        />
      </div>
    );
  }

  const isProcessing = PROCESSING_STATES.has(
    data.status.toLowerCase()
  );

  if (isProcessing || !data.report) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center gap-3 mb-8">
          <StatusBadge status={data.status} />

          <p className="text-sm text-ink-muted">
            Processing your research query…
          </p>
        </div>

        <ReportSkeleton />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={() => router.back()}
            className="shrink-0 p-1.5 rounded-lg hover:bg-card transition-colors text-ink-muted hover:text-ink"
            aria-label="Go back"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <h1 className="text-sm font-medium text-ink truncate">
            {truncate(data.query, 80)}
          </h1>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => {
              void handleTogglePin();
            }}
            className={`p-1.5 rounded-lg transition-colors ${
              data.is_pinned
                ? "text-signal-amber bg-signal-amber-dim"
                : "text-ink-muted hover:text-ink hover:bg-card"
            }`}
            title={data.is_pinned ? "Unpin report" : "Pin report"}
            aria-label={data.is_pinned ? "Unpin report" : "Pin report"}
          >
            <Pin className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => {
              void handleArchive();
            }}
            className="p-1.5 rounded-lg text-ink-muted hover:text-signal-red hover:bg-signal-red-dim transition-colors"
            title="Archive report"
            aria-label="Archive report"
          >
            <Archive className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Report */}
      <ReportViewer
        report={data.report}
        status={data.status}
        processingTimeMs={data.processing_time_ms}
        createdAt={data.created_at}
      />
    </div>
  );
}