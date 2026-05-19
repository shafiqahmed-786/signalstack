import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-12 px-6 text-center gap-3",
        className
      )}
    >
      <div className="w-10 h-10 rounded-xl bg-signal-red-dim border border-signal-red/20 flex items-center justify-center">
        <AlertTriangle className="w-5 h-5 text-signal-red" />
      </div>
      <div>
        <p className="text-sm font-medium text-ink">{title}</p>
        <p className="text-xs text-ink-muted mt-1 max-w-xs leading-relaxed">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-ai border border-ai/30 rounded-md hover:bg-ai-dim transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Try again
        </button>
      )}
    </div>
  );
}