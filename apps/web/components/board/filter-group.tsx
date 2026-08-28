"use client";

import { useState } from "react";

export interface FilterOption {
  key: string;
  label: string;
  count: number;
}

/** How many options a group shows before the rest go behind "mehr". */
const VISIBLE = 5;

/**
 * One <fieldset>/<legend> group of checkboxes (GOV.UK rule: group checkboxes in a
 * fieldset with a legend describing them). OR within the group is the caller's job
 * (lib/filter.ts); this component only reports which keys are checked.
 *
 * Options at count 0 render disabled, never hidden: the evidence-grade group has only two
 * populated values in v1, and hiding the rest would make it look broken rather than
 * honestly sparse. Each option's whole row is the <label>, so the touch target is the full
 * 44px row, not the 16px checkbox glyph.
 *
 * Long groups show their first five and put the rest behind a "mehr" button. The first
 * draft stacked every option of every group in one column, which pushed the entire
 * organisation list below the fold: at 1280x900 a reader saw the heading, the figures and
 * about fifteen checkboxes, and not one organisation. The product is the list; the filter
 * is the instrument. A selected option is always shown even when it sits past the cut, so
 * expanding is never required to see what is currently filtering the page.
 */
export function FilterGroup({
  legend,
  hint,
  hintId,
  options,
  selected,
  onChange,
  idPrefix,
  moreLabel,
  lessLabel,
}: {
  legend: string;
  hint?: string;
  hintId?: string;
  options: FilterOption[];
  selected: ReadonlySet<string>;
  onChange: (next: Set<string>) => void;
  idPrefix: string;
  moreLabel: (n: number) => string;
  lessLabel: string;
}) {
  const [expanded, setExpanded] = useState(false);

  const collapsible = options.length > VISIBLE;
  const shown =
    !collapsible || expanded
      ? options
      : options.filter((opt, i) => i < VISIBLE || selected.has(opt.key));
  const hiddenCount = options.length - shown.length;

  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="text-sm text-ink">{legend}</legend>
      {hint && (
        <p id={hintId} className="mt-1 text-xs text-muted">
          {hint}
        </p>
      )}
      <div className="mt-1">
        {shown.map((opt) => {
          const disabled = opt.count === 0;
          const checked = selected.has(opt.key);
          return (
            <label
              key={opt.key}
              className={`flex min-h-9 cursor-pointer items-center gap-2 py-0.5 text-sm ${
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
                className="dossier-checkbox"
                data-testid={`${idPrefix}-${opt.key}`}
              />
              <span>
                {opt.label} <span className="text-muted">({opt.count})</span>
              </span>
            </label>
          );
        })}
      </div>
      {collapsible && (hiddenCount > 0 || expanded) ? (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          className="mt-1 flex min-h-9 items-center text-sm text-accent underline underline-offset-2"
        >
          {expanded ? lessLabel : moreLabel(hiddenCount)}
        </button>
      ) : null}
    </fieldset>
  );
}
