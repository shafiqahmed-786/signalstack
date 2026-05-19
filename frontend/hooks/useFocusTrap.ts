"use client";

import { useEffect, useRef } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), ' +
  'select:not([disabled]), textarea:not([disabled]), ' +
  '[tabindex]:not([tabindex="-1"]), [contenteditable="true"]';

/**
 * Traps keyboard focus within the referenced container.
 * Restores focus to the previously focused element on cleanup.
 *
 * Pass `enabled = false` to disable the trap without unmounting.
 *
 * Usage:
 *   const ref = useFocusTrap<HTMLDivElement>(isOpen);
 *   <div ref={ref} role="dialog">…</div>
 */
export function useFocusTrap<T extends HTMLElement>(
  enabled = true
): React.RefObject<T> {
  const containerRef = useRef<T>(null);
  const prevFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!enabled) return;

    prevFocusRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const container = containerRef.current;
    if (!container) return;

    // Focus first focusable child
    const firstEl = container.querySelector<HTMLElement>(FOCUSABLE);
    firstEl?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;

      const els = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => !el.hasAttribute("aria-hidden")
      );
      if (els.length === 0) { e.preventDefault(); return; }

      const first = els[0];
      const last  = els[els.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    container.addEventListener("keydown", onKeyDown);

    return () => {
      container.removeEventListener("keydown", onKeyDown);
      prevFocusRef.current?.focus();
    };
  }, [enabled]);

  return containerRef as React.RefObject<T>;
}