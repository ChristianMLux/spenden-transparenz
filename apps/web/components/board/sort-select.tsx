"use client";

import type { FilterState } from "@/lib/filter";

/**
 * Exactly three options, matching the union in lib/filter.ts. There is no fourth
 * option here and there never should be: sorting by evidence grade would rank
 * organisations by how hard we looked, which is the one sort this product refuses to
 * offer (pinned by a tripwire test in lib/filter.test.ts).
 */
export function SortSelect({
  id,
  label,
  value,
  onChange,
  latestLabel,
  nameLabel,
  fewestDataLabel,
}: {
  id: string;
  label: string;
  value: FilterState["sort"];
  onChange: (next: FilterState["sort"]) => void;
  latestLabel: string;
  nameLabel: string;
  fewestDataLabel: string;
}) {
  return (
    <div className="flex min-h-11 items-center gap-2 xl:min-h-9">
      <label htmlFor={id} className="text-sm text-ink">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as FilterState["sort"])}
        className="min-h-11 border border-rule bg-surface px-2 text-sm text-ink xl:min-h-9"
      >
        <option value="latest">{latestLabel}</option>
        <option value="name">{nameLabel}</option>
        <option value="fewest-data">{fewestDataLabel}</option>
      </select>
    </div>
  );
}
