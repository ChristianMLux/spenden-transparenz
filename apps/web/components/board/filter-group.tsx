"use client";

import { useState } from "react";

export interface FilterOption {
  key: string;
  label: string;
  count: number;
}

const VISIBLE = 6;

/**
 * One <fieldset>/<legend> group of checkboxes (GOV.UK rule: group checkboxes in a
 * fieldset with a legend describing them). OR within the group is the caller's job
 * (lib/filter.ts); this component only reports which keys are checked.
 *
 * Options at count 0 render disabled, never hidden: the evidence-grade group has only
 * two populated values in v1, and hiding the rest would make it look broken rather than
 * honestly sparse. Each option's whole row is the <label>, so the touch target is the
 * full 44px row, not the 16px checkbox glyph.
 *
 * Shows the first six options and a "mehr" control for the rest, rather than a
 * multi-column layout: this is what keeps a long group (organisation type, the full
 * closed taxonomy at 11 options) from deciding the rail's height, and by extension —
 * now that the rail sits beside the organisation list rather than above it — never
 * decides where the list starts either (review defect 1). Collapsing never hides a
 * selected option: if a reader's selection lives past the sixth, the group opens
 * already expanded, so ticking a box can never make it disappear from view.
 */
export function FilterGroup({
  legend,
  hint,
  hintId,
  options,
  selected,
  onChange,
  idPrefix,
  showMoreLabel,
  showFewerLabel,
}: {
  legend: string;
  hint?: string;
  hintId?: string;
  options: FilterOption[];
  selected: ReadonlySet<string>;
  onChange: (next: Set<string>) => void;
  idPrefix: string;
  /** Template containing "{count}", e.g. "{count} mehr". */
  showMoreLabel: string;
  showFewerLabel: string;
}) {
  const lastSelectedIndex = options.reduce(
    (max, opt, i) => (selected.has(opt.key) ? i : max),
    -1,
  );
  const [expanded, setExpanded] = useState(lastSelectedIndex >= VISIBLE);

  const hasMore = options.length > VISIBLE;
  const visible = expanded ? options : options.slice(0, VISIBLE);
  const hiddenCount = options.length - VISIBLE;

  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="text-sm text-ink">{legend}</legend>
      {hint && (
        <p id={hintId} className="mt-1 text-xs text-muted">
          {hint}
        </p>
      )}
      <div className="mt-2">
        {visible.map((opt) => {
          const disabled = opt.count === 0;
          const checked = selected.has(opt.key);
          return (
            <label
              key={opt.key}
              // 44px is the touch target: the mobile sheet (below md) needs it. At xl
              // this same component also renders as the always-visible rail, a
              // mouse/trackpad context where the WCAG touch-target rationale does not
              // apply the same way, and the fold (review defect 1) needs the room.
              className={`flex min-h-11 cursor-pointer items-center gap-2 py-1 text-sm xl:min-h-9 ${
                disabled ? "cursor-not-allowed text-muted" : "text-ink"
              }`}
            >
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                aria-describedby={hint ? hintId : undefined}
                onChange={(e) => {
                  const next = new Set(selected);
                  if (e.target.checked) next.add(opt.key);
                  else next.delete(opt.key);
                  onChange(next);
                }}
                className="h-4 w-4 shrink-0 accent-accent"
                data-testid={`${idPrefix}-${opt.key}`}
              />
              <span>
                {opt.label} <span className="text-muted">({opt.count})</span>
              </span>
            </label>
          );
        })}
      </div>
      {hasMore && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="mt-1 min-h-9 text-sm text-accent underline underline-offset-2"
        >
          {(expanded ? showFewerLabel : showMoreLabel).replace("{count}", String(hiddenCount))}
        </button>
      )}
    </fieldset>
  );
}
