/**
 * Lightweight client-side performance tracing.
 *
 * Uses the Performance API (no external dependency).
 * In development: logs traces to the console.
 * In production: no-ops by default (extend `onTrace` to ship to your analytics).
 */

export interface Trace {
  id: string;
  name: string;
  startMs: number;
  endMs?: number;
  durationMs?: number;
  metadata?: Record<string, unknown>;
}

type OnTraceCallback = (trace: Trace) => void;

const store = new Map<string, Trace>();
let _onTrace: OnTraceCallback | null = null;

/** Register a callback for completed traces (e.g., to ship to analytics). */
export function setTraceCallback(cb: OnTraceCallback): void {
  _onTrace = cb;
}

/** Begin a named trace and return its ID. */
export function startTrace(
  name: string,
  metadata?: Record<string, unknown>
): string {
  const id = `${name}__${Date.now()}`;
  store.set(id, { id, name, startMs: performance.now(), metadata });
  return id;
}

/** Finish a trace and return the completed record. */
export function endTrace(id: string): Trace | null {
  const trace = store.get(id);
  if (!trace || trace.endMs !== undefined) return null;

  const endMs = performance.now();
  const completed: Trace = {
    ...trace,
    endMs,
    durationMs: Math.round(endMs - trace.startMs),
  };
  store.set(id, completed);

  if (process.env.NODE_ENV === "development") {
    console.debug(`[perf] ${completed.name}: ${completed.durationMs}ms`, completed.metadata ?? {});
  }

  _onTrace?.(completed);
  return completed;
}

/** Wrap an async function with automatic tracing. */
export async function traceAsync<T>(
  name: string,
  fn: () => Promise<T>,
  metadata?: Record<string, unknown>
): Promise<T> {
  const id = startTrace(name, metadata);
  try {
    return await fn();
  } finally {
    endTrace(id);
  }
}

/** Return all completed traces, sorted by start time. */
export function getCompletedTraces(): Trace[] {
  return Array.from(store.values())
    .filter((t) => t.durationMs !== undefined)
    .sort((a, b) => a.startMs - b.startMs);
}

/** Clear the trace store (call between sessions). */
export function clearTraces(): void {
  store.clear();
}