"use client";

/**
 * The one region a screen-reader user needs to hear change: how many rows survived the
 * current filters. Synchronous, no debounce: this text updates in the same render pass
 * as the checkbox click, never after a delay.
 */
export function ResultCount({ text }: { text: string }) {
  return (
    <p aria-live="polite" className="text-sm text-ink">
      {text}
    </p>
  );
}
