"use client";

export interface FilterOption {
  key: string;
  label: string;
  count: number;
}

/**
 * One <fieldset>/<legend> group of checkboxes (GOV.UK rule: group checkboxes in a
 * fieldset with a legend describing them). OR within the group is the caller's job
 * (lib/filter.ts); this component only reports which keys are checked.
 *
 * Options at count 0 render disabled, never hidden: the evidence-grade group has only
 * two populated values in v1, and hiding the rest would make it look broken rather than
 * honestly sparse. Each option's whole row is the <label>, so the touch target is the
 * full 44px row, not the 16px checkbox glyph.
 */
export function FilterGroup({
  legend,
  hint,
  hintId,
  options,
  selected,
  onChange,
  idPrefix,
}: {
  legend: string;
  hint?: string;
  hintId?: string;
  options: FilterOption[];
  selected: ReadonlySet<string>;
  onChange: (next: Set<string>) => void;
  idPrefix: string;
}) {
  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="text-sm text-ink">{legend}</legend>
      {hint && (
        <p id={hintId} className="mt-1 text-xs text-muted">
          {hint}
        </p>
      )}
      <div className="mt-2">
        {options.map((opt) => {
          const disabled = opt.count === 0;
          const checked = selected.has(opt.key);
          return (
            <label
              key={opt.key}
              className={`flex min-h-11 cursor-pointer items-center gap-2 py-1 text-sm ${
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
    </fieldset>
  );
}
