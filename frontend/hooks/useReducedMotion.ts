"use client";

import { useEffect, useState } from "react";

/**
 * Returns `true` when the user has opted into reduced motion via the
 * `prefers-reduced-motion: reduce` media query.
 *
 * SSR-safe: returns `false` during server render and updates reactively
 * when the system preference changes at runtime.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);

    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return reduced;
}

/**
 * Returns a CSS transition-duration string respecting the user's
 * motion preference.
 *
 * Usage:
 *   const dur = useMotionDuration("200ms");
 *   <div style={{ transitionDuration: dur }} />
 */
export function useMotionDuration(normalDuration: string): string {
  const reduced = useReducedMotion();
  return reduced ? "0ms" : normalDuration;
}

/**
 * Returns Tailwind animation class names conditioned on the user's
 * motion preference. Pass `""` to suppress the animation.
 */
export function useAnimationClass(animationClass: string): string {
  const reduced = useReducedMotion();
  return reduced ? "" : animationClass;
}