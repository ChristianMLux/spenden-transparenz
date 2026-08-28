"use client";

import type { FilterState } from "@/lib/filter";

/** Text tabs with an underline, per DESIGN.md 6.1 ("tabs as text tabs with an
 * underline, not pills"). Standard WAI-ARIA tabs pattern: role="tablist"/"tab". */
export function BoardTabs({
  active,
  onChange,
  orgsLabel,
  chronologicalLabel,
}: {
  active: FilterState["tab"];
  onChange: (next: FilterState["tab"]) => void;
  orgsLabel: string;
  chronologicalLabel: string;
}) {
  const tabs: { key: FilterState["tab"]; label: string }[] = [
    { key: "orgs", label: orgsLabel },
    { key: "chronological", label: chronologicalLabel },
  ];
  return (
    <div role="tablist" className="flex gap-6 border-b border-rule">
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          role="tab"
          aria-selected={active === t.key}
          onClick={() => onChange(t.key)}
          className={`min-h-11 border-b-2 px-1 text-sm ${
            active === t.key ? "border-accent text-ink" : "border-transparent text-muted"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
