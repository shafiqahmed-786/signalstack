import type { SSEClientOptions } from "../api/sse";
import { startResearchStream } from "../api/sse";

export interface ReconnectConfig {
  maxAttempts: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffFactor: number;
}

export interface ReconnectMetrics {
  attemptCount: number;
  totalDelayMs: number;
  lastErrorAt: number | null;
}

const DEFAULT_CONFIG: ReconnectConfig = {
  maxAttempts: 3,
  initialDelayMs: 1_000,
  maxDelayMs: 12_000,
  backoffFactor: 2,
};

function backoffDelay(attempt: number, cfg: ReconnectConfig): number {
  return Math.min(cfg.initialDelayMs * Math.pow(cfg.backoffFactor, attempt - 1), cfg.maxDelayMs);
}

/**
 * Wraps startResearchStream with exponential-backoff automatic reconnect.
 *
 * Calls onReconnect(attempt, delayMs) before each reconnect attempt so the
 * UI can surface a "Reconnecting…" banner.
 *
 * Returns { abort } to cancel the stream and any pending reconnect.
 */
export function connectWithReconnect(
  options: SSEClientOptions,
  config: Partial<ReconnectConfig> = {},
  onReconnect?: (attempt: number, delayMs: number) => void,
): { abort: () => void; metrics: ReconnectMetrics } {
  const cfg: ReconnectConfig = { ...DEFAULT_CONFIG, ...config };
  const metrics: ReconnectMetrics = { attemptCount: 0, totalDelayMs: 0, lastErrorAt: null };

  let aborted = false;
  let currentController: AbortController | null = null;
  let retryHandle: ReturnType<typeof setTimeout> | null = null;

  function connect(attempt: number): void {
    if (aborted) return;
    metrics.attemptCount = attempt;

    const wrapped: SSEClientOptions = {
      ...options,
      onError: (err: Error) => {
        metrics.lastErrorAt = Date.now();

        if (attempt >= cfg.maxAttempts || aborted) {
          options.onError(err);
          return;
        }

        const delay = backoffDelay(attempt, cfg);
        metrics.totalDelayMs += delay;
        onReconnect?.(attempt, delay);

        retryHandle = setTimeout(() => connect(attempt + 1), delay);
      },
    };

    // startResearchStream is async but returns a controller; fire and store
    startResearchStream(wrapped).then((ctrl) => {
      currentController = ctrl;
    });
  }

  connect(1);

  return {
    abort: () => {
      aborted = true;
      if (retryHandle) clearTimeout(retryHandle);
      currentController?.abort();
    },
    metrics,
  };
}