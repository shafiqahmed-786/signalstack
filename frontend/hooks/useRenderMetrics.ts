"use client";

import { useEffect, useRef } from "react";

/**
 * Measures and logs component mount + re-render timing in development.
 *
 * No-ops in production — zero runtime cost when NODE_ENV !== "development".
 *
 * Usage:
 *   useRenderMetrics("ReportViewer");
 */
export function useRenderMetrics(
  componentName: string,
  enabled = true
): void {
  const mountedAtMs = useRef<number>(0);
  const renderCount = useRef(0);

  if (typeof window !== "undefined" && mountedAtMs.current === 0) {
    mountedAtMs.current = performance.now();
  }

  renderCount.current += 1;

  useEffect(() => {
    if (!enabled || process.env.NODE_ENV !== "development") return;
    const mountMs = Math.round(performance.now() - mountedAtMs.current);
    console.debug(`[render] ${componentName} — mounted in ${mountMs}ms`);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!enabled || process.env.NODE_ENV !== "development") return;
    if (renderCount.current <= 1) return;
    console.debug(
      `[render] ${componentName} — re-render #${renderCount.current}`
    );
  });
}

/**
 * Returns a ref-stable callback that records a named timing mark.
 * Useful for measuring user interaction → visible-change latency.
 *
 * Usage:
 *   const mark = useTimingMark("report-section-visible");
 *   useEffect(() => { if (data) mark(); }, [data]);
 */
export function useTimingMark(label: string): () => void {
  const startMs = useRef(performance.now());

  return () => {
    const delta = Math.round(performance.now() - startMs.current);
    if (process.env.NODE_ENV === "development") {
      console.debug(`[timing] ${label}: ${delta}ms from mount`);
    }
  };
}