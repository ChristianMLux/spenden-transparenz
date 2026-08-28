"use client";

import type { FilterOption } from "./filter-group";
import { FilterGroup } from "./filter-group";
import { MobileFilterSheet } from "./mobile-filter-sheet";

export interface FilterBarLabels {
  hint: string;
  districtLegend: string;
  hqLegend: string;
  orgTypeLegend: string;
  verificationLegend: string;
  searchLegend: string;
  searchLabel: string;
  mobileTitle: string;
  mobileClose: string;
  mobileOpen: string; // already formatted, e.g. "Filter (2)"
  /** Already-formatted "mehr" labels, indexed by how many options are hidden. */
  moreLabels: Record<number, string>;
  moreLabelFallback: string;
  lessLabel: string;
}

interface Groups {
  district: FilterOption[];
  hq: FilterOption[];
  orgType: FilterOption[];
  verification: FilterOption[];
}

/**
 * The filter bar. On xl/md it renders as an always-visible column; on base it moves
 * into a sheet opened by a button labelled with the active filter count (DESIGN.md
 * 8.2). Both are the same set of controls, not two independent copies of state: they
 * share the caller's filters object and onChange, so a change made in one place is
 * immediately reflected if the other were visible too.
 *
 * No submit button anywhere here: every control fires onChange immediately (MoJ's own
 * usability finding, cited in DESIGN.md section 2, is why this product does not repeat
 * that mistake).
 */
export function FilterBar({
  groups,
  selected,
  onGroupChange,
  q,
  onQChange,
  sort,
  labels,
  mobileOpen,
  onMobileOpenChange,
}: {
  groups: Groups;
  selected: { district: Set<string>; hq: Set<string>; orgType: Set<string>; verification: Set<string> };
  onGroupChange: (group: keyof Groups, next: Set<string>) => void;
  q: string;
  onQChange: (next: string) => void;
  sort: React.ReactNode;
  labels: FilterBarLabels;
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
}) {
  const fieldsets = (idPrefix: string) => (
    <div className="divide-y divide-chrome-rule space-y-6 [&>*]:pt-6 [&>*:first-child]:pt-0">
      <div>
        <label htmlFor={`${idPrefix}-q`} className="text-sm text-chrome-ink">
          {labels.searchLegend}
        </label>
        <input
          id={`${idPrefix}-q`}
          type="search"
          value={q}
          onChange={(e) => onQChange(e.target.value)}
          placeholder={labels.searchLabel}
          className="mt-2 min-h-11 w-full border border-chrome-rule bg-transparent px-3 text-sm text-chrome-ink placeholder:text-chrome-muted"
        />
      </div>
      <FilterGroup
        moreLabel={(n) => labels.moreLabels[n] ?? labels.moreLabelFallback}
        lessLabel={labels.lessLabel}
        legend={labels.districtLegend}
        options={groups.district}
        selected={selected.district}
        onChange={(next) => onGroupChange("district", next)}
        idPrefix={`${idPrefix}-district`}
      />
      <FilterGroup
        moreLabel={(n) => labels.moreLabels[n] ?? labels.moreLabelFallback}
        lessLabel={labels.lessLabel}
        legend={labels.hqLegend}
        options={groups.hq}
        selected={selected.hq}
        onChange={(next) => onGroupChange("hq", next)}
        idPrefix={`${idPrefix}-hq`}
      />
      <FilterGroup
        moreLabel={(n) => labels.moreLabels[n] ?? labels.moreLabelFallback}
        lessLabel={labels.lessLabel}
        legend={labels.orgTypeLegend}
        options={groups.orgType}
        selected={selected.orgType}
        onChange={(next) => onGroupChange("orgType", next)}
        idPrefix={`${idPrefix}-orgtype`}
      />
      <FilterGroup
        moreLabel={(n) => labels.moreLabels[n] ?? labels.moreLabelFallback}
        lessLabel={labels.lessLabel}
        legend={labels.verificationLegend}
        hint={labels.hint}
        hintId={`${idPrefix}-verification-hint`}
        options={groups.verification}
        selected={selected.verification}
        onChange={(next) => onGroupChange("verification", next)}
        idPrefix={`${idPrefix}-verification`}
      />
      {sort}
    </div>
  );

  return (
    <div>
      {/* base: a trigger button that opens the sheet */}
      <div className="md:hidden">
        <button
          type="button"
          onClick={() => onMobileOpenChange(true)}
          className="min-h-11 border border-chrome-rule px-3 text-sm text-chrome-ink"
        >
          {labels.mobileOpen}
        </button>
        <MobileFilterSheet
          open={mobileOpen}
          onOpenChange={onMobileOpenChange}
          title={labels.mobileTitle}
          closeLabel={labels.mobileClose}
        >
          {fieldsets("m")}
        </MobileFilterSheet>
      </div>

      {/* md/xl: always visible */}
      <div className="hidden md:block" data-testid="filter-bar-desktop">
        {fieldsets("d")}
      </div>
    </div>
  );
}
