"use client";

import { useState } from "react";
import { WifiOff, RotateCcw, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface StreamReconnectBannerProps {
  attempt: number;
  delayMs: number;
  onForceRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function StreamReconnectBanner({
  attempt,
  delayMs,
  onForceRetry,
  onDismiss,
  className,
}: StreamReconnectBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  const delaySec = Math.ceil(delayMs / 1000);

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-xl border animate-slide-up",
        "border-signal-amber/30 bg-signal-amber-dim",
        className
      )}
    >
      <WifiOff
        className="w-4 h-4 text-signal-amber shrink-0"
        aria-hidden="true"
      />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-signal-amber leading-none">
          Stream disconnected
        </p>
        <p className="text-xs text-ink-muted mt-0.5">
          Reconnecting — attempt{" "}
          <span className="font-mono text-ink-secondary">{attempt}</span>
          {delaySec > 0 && (
            <>
              {" "}· retrying in{" "}
              <span className="font-mono text-ink-secondary">{delaySec}s</span>
            </>
          )}
        </p>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        {onForceRetry && (
          <button
            onClick={onForceRetry}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-ink-secondary hover:text-ink hover:bg-surface/50 transition-colors"
            aria-label="Force reconnect now"
          >
            <RotateCcw className="w-3 h-3" />
            Retry now
          </button>
        )}
        <button
          onClick={handleDismiss}
          className="p-1 rounded text-ink-muted hover:text-ink hover:bg-surface/50 transition-colors"
          aria-label="Dismiss reconnect notification"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}