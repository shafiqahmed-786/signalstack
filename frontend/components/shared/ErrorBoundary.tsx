"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  /** Custom fallback UI — overrides the default error card */
  fallback?: ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
  showReset?: boolean;
  resetLabel?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * React error boundary — must be a class component per the React spec.
 *
 * Usage:
 *   <ErrorBoundary showReset>
 *     <SomeFeature />
 *   </ErrorBoundary>
 *
 * For HOC usage: `withErrorBoundary(MyComponent)`
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    this.props.onError?.(error, info);
    if (process.env.NODE_ENV === "development") {
      console.error("[ErrorBoundary]", error, info.componentStack);
    }
  }

  reset = (): void => this.setState({ hasError: false, error: null });

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    return (
      <div
        role="alert"
        className="flex flex-col items-center justify-center py-16 px-6 text-center gap-4"
      >
        <div className="w-12 h-12 rounded-xl bg-signal-red-dim border border-signal-red/20 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6 text-signal-red" aria-hidden="true" />
        </div>
        <div className="space-y-1 max-w-sm">
          <h2 className="text-sm font-semibold text-ink">Something went wrong</h2>
          <p className="text-xs text-ink-muted leading-relaxed">
            {this.state.error?.message ?? "An unexpected error occurred in this section."}
          </p>
        </div>
        {this.props.showReset !== false && (
          <button
            onClick={this.reset}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-ai border border-ai/30 rounded-md hover:bg-ai-dim transition-colors"
          >
            <RefreshCw className="w-3 h-3" aria-hidden="true" />
            {this.props.resetLabel ?? "Try again"}
          </button>
        )}
      </div>
    );
  }
}

/** HOC wrapper for functional component usage. */
export function withErrorBoundary<P extends object>(
  Wrapped: React.ComponentType<P>,
  boundaryProps?: Omit<Props, "children">
): React.FC<P> {
  const WithBoundary: React.FC<P> = (props) => (
    <ErrorBoundary {...boundaryProps}>
      <Wrapped {...props} />
    </ErrorBoundary>
  );
  WithBoundary.displayName =
    `withErrorBoundary(${Wrapped.displayName ?? Wrapped.name})`;
  return WithBoundary;
}