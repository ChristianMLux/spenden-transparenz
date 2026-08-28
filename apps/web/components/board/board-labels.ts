// Plain-string labels for the client filter island (board-explorer.tsx and everything it
// renders directly). The root layout ships an EMPTY message catalogue to the client
// (see app/[locale]/layout.tsx), so nothing under a "use client" boundary may call
// useTranslations itself; this file's shape is what page.tsx fills in on the server,
// once, with next-intl available, and hands down as plain serialisable props.
//
// Anything that depends on a value the client can produce on its own without a library
// (a bounded count, an enumerable facet key) is precomputed here rather than partially
// re-implemented client-side. The one exception is the free-text search query, which
// never needs translating because it is the reader's own words.
export interface BoardLabels {
  numberLine: { orgs: string; statements: string; districts: string; noResponse: string };
  dataStand: string;
  sourcesLink: string;
  /** Precomputed locale-aware href ("/de/quellen" / "/en/sources"), so the client never
   * needs @/i18n/navigation's Link (its pathname-translation runtime alone is ~21 KB
   * gz) for what is, on this page, a single static link to a page that never changes
   * with the filter state. */
  sourcesHref: string;
  tabs: { orgs: string; chronological: string };
  /** Indexed by the filtered count. resultCountOrgs[3] is "3 von 44 Organisationen". */
  resultCountOrgs: string[];
  resultCountStatements: string[];
  filters: {
    hint: string;
    districtLegend: string;
    hqLegend: string;
    orgTypeLegend: string;
    verificationLegend: string;
    searchLegend: string;
    searchLabel: string;
    sortLabel: string;
    sortLatest: string;
    sortName: string;
    sortFewestData: string;
    selectedHeading: string;
    clearAll: string;
    /** Indexed by the number of active filter values. mobileOpenLabels[2] is "Filter (2)". */
    mobileOpenLabels: string[];
    mobileClose: string;
    mobileTitle: string;
    searchChipPrefix: string;
    removeSearchLabel: string;
  };
  /** Facet key (district code, "local"/"international", an OrgType, a Verification) to
   * its display word. One flat map: the four key namespaces never collide. */
  optionLabel: Record<string, string>;
  /** Facet key to the full localised "remove this filter" sentence. */
  removeChipLabel: Record<string, string>;
  locatorCaption: string;
}
