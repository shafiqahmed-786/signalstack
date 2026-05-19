"use client";

import { useEffect, useRef } from "react";

type Modifier = "ctrl" | "meta" | "shift" | "alt";

export interface Shortcut {
  /** Key name (e.g. "k", "Escape") — matched against `KeyboardEvent.key` */
  key: string;
  /** Required modifier keys. All others must be absent unless listed. */
  modifiers?: Modifier[];
  handler: (e: KeyboardEvent) => void;
  /** Call `e.preventDefault()` when the shortcut fires */
  preventDefault?: boolean;
  /**
   * When `true` (default), the shortcut is suppressed while an
   * input, textarea, or contenteditable element has focus.
   */
  ignoreInInput?: boolean;
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.isContentEditable
  );
}

function shortcutMatches(e: KeyboardEvent, s: Shortcut): boolean {
  if (e.key !== s.key) return false;
  const mods = s.modifiers ?? [];
  if (mods.includes("ctrl")  !== e.ctrlKey)  return false;
  if (mods.includes("meta")  !== e.metaKey)  return false;
  if (mods.includes("shift") !== e.shiftKey) return false;
  if (mods.includes("alt")   !== e.altKey)   return false;
  return true;
}

/**
 * Registers keyboard shortcuts declaratively.
 *
 * Shortcuts ref is kept current without re-adding listeners.
 *
 * Usage:
 *   useKeyboard([
 *     { key: "k", modifiers: ["meta"], handler: openPalette, preventDefault: true },
 *     { key: "Escape", handler: closeModal, ignoreInInput: false },
 *   ]);
 */
export function useKeyboard(shortcuts: Shortcut[]): void {
  const ref = useRef<Shortcut[]>(shortcuts);
  ref.current = shortcuts;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      for (const s of ref.current) {
        const skipInput = s.ignoreInInput !== false;
        if (skipInput && isEditableTarget(e.target)) continue;
        if (!shortcutMatches(e, s)) continue;
        if (s.preventDefault) e.preventDefault();
        s.handler(e);
        return; // First matching shortcut wins
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []); // stable — ref keeps shortcuts current
}