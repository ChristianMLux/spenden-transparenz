"use client";

export interface Chip {
  key: string;
  label: string;
  removeLabel: string;
}

/**
 * Active filters as removable chips under a "Selected" heading, plus a clear-all link.
 * Renders nothing when no filter is active, so the empty state costs no vertical space.
 */
export function FilterChips({
  heading,
  clearAllLabel,
  chips,
  onRemove,
  onClearAll,
}: {
  heading: string;
  clearAllLabel: string;
  chips: Chip[];
  onRemove: (key: string) => void;
  onClearAll: () => void;
}) {
  if (chips.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-muted">{heading}</span>
      {chips.map((c) => (
        <button
          key={c.key}
          type="button"
          onClick={() => onRemove(c.key)}
          aria-label={c.removeLabel}
          className="inline-flex min-h-11 items-center gap-1 border border-accent px-3 text-sm text-accent"
          style={{ borderRadius: 2 }}
        >
          <span>{c.label}</span>
          <span aria-hidden="true">×</span>
        </button>
      ))}
      <button
        type="button"
        onClick={onClearAll}
        className="min-h-11 px-1 text-sm text-accent underline-offset-2 hover:underline"
      >
        {clearAllLabel}
      </button>
    </div>
  );
}
