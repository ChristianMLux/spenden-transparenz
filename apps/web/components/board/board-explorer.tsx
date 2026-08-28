"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  applyFilters,
  countFacets,
  EMPTY,
  flattenStatements,
  parseFilters,
  serializeFilters,
} from "@/lib/filter";
import type { FilterState } from "@/lib/filter";
import type { BoardData, Responder } from "@/lib/types";
import type { BoardLabels } from "./board-labels";
import { BoardTabs } from "./board-tabs";
import { dayKeyOf } from "./chronological";
import type { Chip } from "./filter-chips";
import { FilterChips } from "./filter-chips";
import type { FilterOption } from "./filter-group";
import { FilterBar } from "./filter-bar";
import { ResultCount } from "./result-count";
import { SortSelect } from "./sort-select";

const rowKey = (r: Responder) => r.org_id ?? r.org_name_raw;

function readFiltersFromLocation(): FilterState {
  if (typeof window === "undefined") return EMPTY;
  return parseFilters(new URLSearchParams(window.location.search));
}

/**
 * Splits an already-translated, already-pluralised string like "44 Organisationen" into
 * its leading number and the word that follows, purely for a visual size split (a large
 * numeral over a small label). Neither locale's copy changes: the same characters render,
 * only inside two spans instead of one, with a real space text node between them so the
 * combined accessible name is unchanged ("44 Organisationen", not "44Organisationen").
 * Falls back to rendering the whole string as the numeral if the shape is ever
 * unexpected, rather than losing text.
 */
function splitNumberLabel(text: string): [string, string] {
  const m = text.match(/^(\S+)\s+(.*)$/);
  return m ? [m[1] ?? text, m[2] ?? ""] : [text, ""];
}

function FigureTile({
  href,
  text,
  onClick,
}: {
  href: string;
  text: string;
  onClick: () => void;
}) {
  const [number, label] = splitNumberLabel(text);
  return (
    <a
      href={href}
      onClick={(e) => {
        e.preventDefault();
        onClick();
      }}
      className="figure-tile flex min-h-11 flex-col justify-center gap-0.5 px-4 py-2 text-chrome-ink no-underline sm:px-5"
    >
      <span className="block text-2xl font-semibold text-chrome-ink">{number}</span>{" "}
      <span className="block text-xs text-chrome-muted">{label}</span>
    </a>
  );
}

/**
 * The four number-line destinations. Every number in board.counts becomes a distinct,
 * meaningful FilterState, not just a decorative statistic:
 *  - org count            -> tab A, every filter cleared
 *  - statement count       -> tab B (chronological), which is literally the list of
 *                             every evidenced statement, so no other filter is needed
 *  - district count        -> tab A, every named district selected (the complement of
 *                             "no location stated"), showing exactly the responders
 *                             that have a stated place
 *  - orgs without response -> tab A, hasResponse: false, showing exactly those nine.
 *                             This started as a sort, on the reasoning that a hidden
 *                             "has no statement" field could let a filter remove the very
 *                             organisations the product insists on always showing. The
 *                             instinct was right and is now encoded as a test instead: the
 *                             filter can SHOW the organisations without a response and can
 *                             never hide one for lacking a response. A reader who clicks a
 *                             count of nine should get nine rows, not forty-four reordered.
 */
function numberLineTargets(board: BoardData): Record<"orgs" | "statements" | "districts" | "noResponse", FilterState> {
  const realDistricts = board.facets.districts.filter((f) => f.key !== "none").map((f) => f.key);
  return {
    orgs: { ...EMPTY },
    statements: { ...EMPTY, tab: "chronological" },
    districts: { ...EMPTY, districts: realDistricts },
    noResponse: { ...EMPTY, hasResponse: false },
  };
}

export function BoardExplorer({
  board,
  rowNodes,
  chronoNodes,
  dayLabels,
  labels,
  intro,
}: {
  board: BoardData;
  rowNodes: Record<string, ReactNode>;
  chronoNodes: Record<string, ReactNode>;
  dayLabels: Record<string, string>;
  labels: BoardLabels;
  /** The server-rendered h1 + GLIDE id + scope sentence. Rendered after the chrome's
   * figure strip: the masthead and the figures are one navy block, this heading is the
   * canvas's own first thing below it. */
  intro: ReactNode;
}) {
  const [filters, setFiltersState] = useState<FilterState>(EMPTY);
  const [hydrated, setHydrated] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Read the shared URL once, after mount. Not useSearchParams(): that hook forces the
  // whole subtree that calls it into client-only rendering during static generation
  // (see its own docs), which would cost the org rows their prerendered HTML for no
  // benefit here, since board data never needs a server round-trip to filter.
  //
  // This is the documented exception to "don't setState in an effect": window.location
  // does not exist on the server, so the server-rendered (and pre-hydration client)
  // output must be EMPTY, and the real, possibly-filtered state can only be read once
  // the browser APIs exist. Computing it during render, or via a lazy useState
  // initializer, would make the client's first render diverge from the server-rendered
  // HTML for any shared, pre-filtered link and trip a hydration mismatch instead.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- see comment above
    setFiltersState(readFiltersFromLocation());
    setHydrated(true);
  }, []);

  // Keep the URL in sync for shareable links, via the raw History API rather than
  // next/navigation's router: a searchParams-only update on this route never needs a
  // new render from the server (nothing here reads searchParams as a page prop), so
  // there is nothing to gain from routing through the framework router for it, and
  // doing it directly guarantees this can never add a network round-trip to a filter
  // click regardless of how the router's own caching behaves.
  useEffect(() => {
    if (!hydrated) return;
    const qs = serializeFilters(filters).toString();
    const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState(null, "", url);
  }, [filters, hydrated]);

  const setFilters = useCallback((next: FilterState) => setFiltersState(next), []);

  const filteredResponders = useMemo(() => applyFilters(board.responders, filters), [board.responders, filters]);
  const liveFacets = useMemo(() => countFacets(filteredResponders), [filteredResponders]);

  const targets = useMemo(() => numberLineTargets(board), [board]);

  const activeFilterCount =
    filters.districts.length +
    filters.hq.length +
    filters.orgTypes.length +
    filters.verification.length +
    (filters.q.trim() ? 1 : 0) +
    (filters.hasResponse !== null ? 1 : 0);

  // Every option in board.facets is shown even at zero (the canonical, exhaustive key
  // list); the count shown next to it narrows live as other filters are applied.
  const mergeOptions = (
    canonical: BoardData["facets"]["hq"],
    live: BoardData["facets"]["hq"],
    labelFor: (key: string) => string,
  ): FilterOption[] =>
    canonical.map((f) => ({
      key: f.key,
      label: labelFor(f.key),
      count: live.find((x) => x.key === f.key)?.count ?? 0,
    }));

  const groups = {
    district: mergeOptions(board.facets.districts, liveFacets.districts, (k) => labels.optionLabel[k] ?? k),
    hq: mergeOptions(board.facets.hq, liveFacets.hq, (k) => labels.optionLabel[k] ?? k),
    orgType: mergeOptions(board.facets.orgType, liveFacets.orgType, (k) => labels.optionLabel[k] ?? k),
    verification: mergeOptions(board.facets.verification, liveFacets.verification, (k) => labels.optionLabel[k] ?? k),
  };

  const selected = {
    district: new Set(filters.districts),
    hq: new Set(filters.hq),
    orgType: new Set(filters.orgTypes),
    verification: new Set(filters.verification),
  };

  const onGroupChange = (group: keyof typeof groups, next: Set<string>) => {
    const values = [...next];
    if (group === "district") setFilters({ ...filters, districts: values });
    else if (group === "hq") setFilters({ ...filters, hq: values as FilterState["hq"] });
    else if (group === "orgType") setFilters({ ...filters, orgTypes: values });
    else setFilters({ ...filters, verification: values });
  };

  const chips: Chip[] = [
    ...filters.districts.map((key) => ({
      key: `districts:${key}`,
      label: labels.optionLabel[key] ?? key,
      removeLabel: labels.removeChipLabel[key] ?? labels.optionLabel[key] ?? key,
    })),
    ...filters.hq.map((key) => ({
      key: `hq:${key}`,
      label: labels.optionLabel[key] ?? key,
      removeLabel: labels.removeChipLabel[key] ?? labels.optionLabel[key] ?? key,
    })),
    ...filters.orgTypes.map((key) => ({
      key: `orgTypes:${key}`,
      label: labels.optionLabel[key] ?? key,
      removeLabel: labels.removeChipLabel[key] ?? labels.optionLabel[key] ?? key,
    })),
    ...filters.verification.map((key) => ({
      key: `verification:${key}`,
      label: labels.optionLabel[key] ?? key,
      removeLabel: labels.removeChipLabel[key] ?? labels.optionLabel[key] ?? key,
    })),
    ...(filters.q.trim()
      ? [{ key: "q", label: `${labels.filters.searchChipPrefix} ${filters.q}`, removeLabel: labels.filters.removeSearchLabel }]
      : []),
  ];

  const removeChip = (chipKey: string) => {
    const [group, value] = chipKey.split(":", 2);
    if (group === "q") setFilters({ ...filters, q: "" });
    else if (group === "districts") setFilters({ ...filters, districts: filters.districts.filter((v) => v !== value) });
    else if (group === "hq") setFilters({ ...filters, hq: filters.hq.filter((v) => v !== value) as FilterState["hq"] });
    else if (group === "orgTypes") setFilters({ ...filters, orgTypes: filters.orgTypes.filter((v) => v !== value) });
    else if (group === "verification")
      setFilters({ ...filters, verification: filters.verification.filter((v) => v !== value) });
  };

  const resultCountText =
    filters.tab === "orgs"
      ? (labels.resultCountOrgs[filteredResponders.length] ?? String(filteredResponders.length))
      : (labels.resultCountStatements[flattenStatements(filteredResponders).length] ??
         String(flattenStatements(filteredResponders).length));

  // The named districts, each a link that selects exactly that district. Same
  // destinations the "6 Distrikte" figure covers, spelled out. "none" is left out: it is
  // a filter value, not a place, and listing it among place names would read as one.
  const districtLinks = board.facets.districts
    .filter((d) => d.key !== "none" && d.count > 0)
    .map((d) => ({
      key: d.key,
      label: labels.optionLabel[d.key] ?? d.key,
      filters: { ...EMPTY, districts: [d.key] } as FilterState,
    }));

  const numberLine: { key: keyof typeof targets; text: string }[] = [
    { key: "orgs", text: labels.numberLine.orgs },
    { key: "statements", text: labels.numberLine.statements },
    { key: "districts", text: labels.numberLine.districts },
    { key: "noResponse", text: labels.numberLine.noResponse },
  ];

  return (
    <div>
      {/* The chrome: figure tiles directly under the masthead's wordmark, full-bleed to
          the viewport edge so the navy band reads as one continuous shape with the
          header above it. Each tile is still the same filter link it was as a sentence. */}
      <div className="chrome-bleed chrome-bleed-flush-top bg-chrome">
        <div className="figure-strip mx-auto max-w-[80rem]">
          {numberLine.map((n) => (
            <FigureTile
              key={n.key}
              href={`?${serializeFilters(targets[n.key]).toString()}`}
              text={n.text}
              onClick={() => setFilters(targets[n.key])}
            />
          ))}
        </div>
      </div>

      <div className="mt-3">{intro}</div>

      <p className="mt-1 text-xs text-muted">
        {labels.dataStand}
        {" · "}
        {/* A plain anchor with a server-precomputed href, not @/i18n/navigation's
            Link: see board-labels.ts on sourcesHref for why. Permanently underlined,
            not hover-only: this link sits inline in a sentence next to plain text of a
            similar colour, and WCAG 1.4.1 (axe: link-in-text-block) requires more than
            colour alone to tell the two apart. */}
        <a href={labels.sourcesHref} className="text-accent underline underline-offset-2">
          {labels.sourcesLink}
        </a>
      </p>

      {/* The districts as plain links, where the locator drawing used to be. The drawing
          was an invented outline of Nepal with district marks placed roughly, and on a
          product whose whole claim is that nothing is invented, a fabricated map is the
          worst possible first graphic. There is no attributable geometry in the repo, so
          rather than redraw one from memory the names carry the same information and can
          be sourced. A real outline is post-v1, from Natural Earth or GADM with its
          licence. */}
      <p className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-sm">
        <span className="text-muted">{labels.districtsLabel}</span>
        {districtLinks.map((d, i) => (
          <span key={d.key}>
            <a
              href={`?${serializeFilters(d.filters).toString()}`}
              onClick={(e) => {
                e.preventDefault();
                setFilters(d.filters);
              }}
              className="text-accent underline-offset-2 hover:underline"
            >
              {d.label}
            </a>
            {i < districtLinks.length - 1 && <span className="text-muted"> · </span>}
          </span>
        ))}
      </p>

      <hr className="my-2 border-rule" />

      {/* Rail on the left, results beside it. Before this the filters ran the full width
          and the list began underneath them, so the first screen held no organisation at
          all. */}
      <div className="grid gap-4 xl:grid-cols-[16rem_1fr] xl:gap-8">
        <div className="filter-rail-bleed bg-chrome px-4 py-6 xl:sticky xl:top-4 xl:self-start xl:px-5">
        <FilterBar
          groups={groups}
          selected={selected}
          onGroupChange={onGroupChange}
          q={filters.q}
          onQChange={(next) => setFilters({ ...filters, q: next })}
          sort={
            filters.tab === "orgs" ? (
              <SortSelect
                id="board-sort"
                label={labels.filters.sortLabel}
                value={filters.sort}
                onChange={(next) => setFilters({ ...filters, sort: next })}
                latestLabel={labels.filters.sortLatest}
                nameLabel={labels.filters.sortName}
                fewestDataLabel={labels.filters.sortFewestData}
              />
            ) : null
          }
          labels={{
            hint: labels.filters.hint,
            districtLegend: labels.filters.districtLegend,
            hqLegend: labels.filters.hqLegend,
            orgTypeLegend: labels.filters.orgTypeLegend,
            verificationLegend: labels.filters.verificationLegend,
            searchLegend: labels.filters.searchLegend,
            searchLabel: labels.filters.searchLabel,
            mobileTitle: labels.filters.mobileTitle,
            mobileClose: labels.filters.mobileClose,
            mobileOpen:
              labels.filters.mobileOpenLabels[activeFilterCount] ?? labels.filters.mobileOpenLabels[0] ?? "",
            moreLabels: labels.filters.moreLabels,
            moreLabelFallback: labels.filters.moreLabelFallback,
            lessLabel: labels.filters.lessLabel,
          }}
          mobileOpen={mobileOpen}
          onMobileOpenChange={setMobileOpen}
        />
        </div>

        <div className="min-w-0">
      <BoardTabs
        active={filters.tab}
        onChange={(next) => setFilters({ ...filters, tab: next })}
        orgsLabel={labels.tabs.orgs}
        chronologicalLabel={labels.tabs.chronological}
      />

      <div className="mt-3 space-y-1">
        <FilterChips
          heading={labels.filters.selectedHeading}
          clearAllLabel={labels.filters.clearAll}
          chips={chips}
          onRemove={removeChip}
          onClearAll={() => setFilters({ ...EMPTY, tab: filters.tab })}
        />
        <ResultCount text={resultCountText} />
      </div>

      <div className="mt-3">
        {filters.tab === "orgs" ? (
          <div>
            {/* Column headers, table-like: the same fixed-fraction grid every row below
                uses, so the labels line up with the cells without a literal <table>
                (each organisation stays an <article>, which a table row cannot hold). */}
            <div className="board-row-grid hidden border-b border-l-2 border-rule border-l-transparent px-2 pb-1 text-xs text-muted md:grid">
              <span>{labels.columns.organisation}</span>
              <span>{labels.columns.reaktion}</span>
              <span>{labels.columns.ort}</span>
              <span>{labels.columns.quelleUndStand}</span>
              <span>{labels.columns.spenden}</span>
            </div>
            {filteredResponders.map((r) => (
              <div key={rowKey(r)}>{rowNodes[rowKey(r)]}</div>
            ))}
          </div>
        ) : (
          <ChronologicalList
            statements={flattenStatements(filteredResponders)}
            chronoNodes={chronoNodes}
            dayLabels={dayLabels}
          />
        )}
      </div>
        </div>
      </div>
    </div>
  );
}

function ChronologicalList({
  statements,
  chronoNodes,
  dayLabels,
}: {
  statements: ReturnType<typeof flattenStatements>;
  chronoNodes: Record<string, ReactNode>;
  dayLabels: Record<string, string>;
}) {
  const groups: { key: string; items: typeof statements }[] = [];
  for (const s of statements) {
    const key = dayKeyOf(s);
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.items.push(s);
    else groups.push({ key, items: [s] });
  }

  return (
    <div>
      {groups.map((g) => (
        <div key={g.key} className="border-b border-rule py-4 first:pt-0 last:border-b-0">
          <h2 className="text-lg">{dayLabels[g.key] ?? g.key}</h2>
          <div className="mt-3">
            {g.items.map((s) => (
              <div key={s.id} className="border-t border-dashed border-rule pt-3 mt-3 first:mt-0 first:border-t-0 first:pt-0">
                {chronoNodes[s.id]}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
