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
  showMore: string; // "{count} mehr" template, see filter-group.tsx
  showFewer: string;
}

interface Groups {
  district: FilterOption[];
  hq: FilterOption[];
  orgType: FilterOption[];
  verification: FilterOption[];
}

/**
 * The filter rail. On md/xl it renders as an always-visible column to the left of the
 * organisation list (board-explorer.tsx); on base it moves into a sheet opened by a
 * button labelled with the active filter count (DESIGN.md 8.2, corrected by the lead's
 * review: a left rail beside the list, not a bar stacked above it, so the rail's own
 * height never decides where the list starts). Both are the same set of controls, not
 * two independent copies of state: they share the caller's filters object and
 * onChange, so a change made in one place is immediately reflected if the other were
 * visible too.
 *
 * A single column throughout: each group shows its first few options with a "mehr"
 * control for the rest (FilterGroup), which is what keeps a long group like
 * organisation type (11 options, the full closed taxonomy) from growing the rail past
 * a reasonable height, without resorting to multi-column text that wraps badly in a
 * narrow rail.
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
    <div className="space-y-6">
      <div>
        <label htmlFor={`${idPrefix}-q`} className="text-sm text-ink">
          {labels.searchLegend}
        </label>
        <input
          id={`${idPrefix}-q`}
          type="search"
          value={q}
          onChange={(e) => onQChange(e.target.value)}
          placeholder={labels.searchLabel}
          className="mt-2 min-h-11 w-full border border-rule bg-surface px-3 text-sm text-ink xl:min-h-9"
        />
      </div>

      <FilterGroup
        legend={labels.districtLegend}
        options={groups.district}
        selected={selected.district}
        onChange={(next) => onGroupChange("district", next)}
        idPrefix={`${idPrefix}-district`}
        showMoreLabel={labels.showMore}
        showFewerLabel={labels.showFewer}
      />
      <FilterGroup
        legend={labels.hqLegend}
        options={groups.hq}
        selected={selected.hq}
        onChange={(next) => onGroupChange("hq", next)}
        idPrefix={`${idPrefix}-hq`}
        showMoreLabel={labels.showMore}
        showFewerLabel={labels.showFewer}
      />
      <FilterGroup
        legend={labels.orgTypeLegend}
        options={groups.orgType}
        selected={selected.orgType}
        onChange={(next) => onGroupChange("orgType", next)}
        idPrefix={`${idPrefix}-orgtype`}
        showMoreLabel={labels.showMore}
        showFewerLabel={labels.showFewer}
      />
      <FilterGroup
        legend={labels.verificationLegend}
        hint={labels.hint}
        hintId={`${idPrefix}-verification-hint`}
        options={groups.verification}
        selected={selected.verification}
        onChange={(next) => onGroupChange("verification", next)}
        idPrefix={`${idPrefix}-verification`}
        showMoreLabel={labels.showMore}
        showFewerLabel={labels.showFewer}
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
          className="min-h-11 border border-rule px-3 text-sm text-ink"
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

      {/* md/xl: always visible, the rail */}
      <div className="hidden md:block" data-testid="filter-bar-desktop">
        {fieldsets("d")}
      </div>
    </div>
  );
}
