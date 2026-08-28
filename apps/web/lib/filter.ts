// The board filter engine: pure functions over already-loaded data, no I/O, no framework
// dependency. 44 rows today, built for the 4400-row future (see the performance test in
// filter.test.ts). Every active filter group is converted to a Set once per call, never
// scanned with Array.includes per row; the name search compares against the precomputed
// `search_key`, never re-normalising per keystroke (that normalisation already happened
// once at build time in lib/api.ts).
import type { BoardData, Datum, Responder, Statement } from "./types";

export interface FilterState {
  /** District codes, plus the literal 'none' for "no location stated". */
  districts: string[];
  hq: ("local" | "international")[];
  orgTypes: string[];
  verification: string[];
  q: string;
  /**
   * true  = only organisations with no found response
   * false = only organisations that have one
   * null  = no opinion, the default
   *
   * Deliberately three-valued. The figure "9 ohne gefundene Reaktion" has to be a real
   * filter like every other figure in that row, and a reader who clicks a count of nine
   * expects nine rows. What this must never become is a way to hide an organisation for
   * having no response: that is the one thing the product refuses to do, so the true case
   * SHOWS those organisations and there is a test for it.
   */
  hasResponse: boolean | null;
  sort: "latest" | "name" | "fewest-data";
  tab: "orgs" | "chronological";
}

export const EMPTY: FilterState = {
  districts: [],
  hq: [],
  orgTypes: [],
  verification: [],
  q: "",
  hasResponse: null,
  sort: "latest",
  tab: "orgs",
};

const fold = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/\s+/g, " ")
    .trim();

// ---------------------------------------------------------------------------
// searchParams <-> FilterState
// ---------------------------------------------------------------------------

const LIST_KEYS = ["districts", "hq", "orgTypes", "verification"] as const;
type ListKey = (typeof LIST_KEYS)[number];

const SORTS: readonly FilterState["sort"][] = ["latest", "name", "fewest-data"];
const TABS: readonly FilterState["tab"][] = ["orgs", "chronological"];

export function parseFilters(sp: URLSearchParams): FilterState {
  const list = (key: ListKey): string[] => {
    const raw = sp.get(key);
    return raw ? raw.split(",").filter(Boolean) : [];
  };
  const sort = sp.get("sort");
  const tab = sp.get("tab");
  return {
    districts: list("districts"),
    hq: list("hq") as FilterState["hq"],
    orgTypes: list("orgTypes"),
    verification: list("verification"),
    q: sp.get("q") ?? "",
    hasResponse: sp.get("hasResponse") === "1" ? true : sp.get("hasResponse") === "0" ? false : null,
    sort: (SORTS as readonly string[]).includes(sort ?? "") ? (sort as FilterState["sort"]) : "latest",
    tab: (TABS as readonly string[]).includes(tab ?? "") ? (tab as FilterState["tab"]) : "orgs",
  };
}

export function serializeFilters(f: FilterState): URLSearchParams {
  const sp = new URLSearchParams();
  for (const key of LIST_KEYS) {
    const values = f[key];
    if (values.length > 0) sp.set(key, values.join(","));
  }
  if (f.q) sp.set("q", f.q);
  if (f.hasResponse !== null) sp.set("hasResponse", f.hasResponse ? "1" : "0");
  if (f.sort !== "latest") sp.set("sort", f.sort);
  if (f.tab !== "orgs") sp.set("tab", f.tab);
  return sp;
}

// ---------------------------------------------------------------------------
// Filtering
//
// OR within a group, AND between groups. An empty group matches everything (it is not
// selected, so it imposes no constraint). A responder with zero statements always
// passes every statement-level filter (district, verification): the absence of a
// reaction is never treated as a non-match and hidden, because "no response" is a
// first-class, always-visible state in this product.
// ---------------------------------------------------------------------------

function statementMatchesDistricts(s: Statement, districts: Set<string>): boolean {
  if (districts.has("none") && s.districts.length === 0) return true;
  return s.districts.some((d) => districts.has(d.code));
}

function statementMatchesVerification(s: Statement, verification: Set<string>): boolean {
  return verification.has(s.datum.verification);
}

function responderMatchesHq(r: Responder, hq: Set<"local" | "international">): boolean {
  if (hq.has("local") && r.is_local) return true;
  if (hq.has("international") && !r.is_local) return true;
  return false;
}

export function applyFilters(responders: Responder[], f: FilterState): Responder[] {
  const districts = new Set(f.districts);
  const hq = new Set(f.hq);
  const orgTypes = new Set(f.orgTypes);
  const verification = new Set(f.verification);
  const q = f.q.trim() ? fold(f.q) : "";

  let result = responders.filter((r) => {
    if (f.hasResponse !== null && r.statements.length > 0 !== f.hasResponse) return false;
    if (hq.size > 0 && !responderMatchesHq(r, hq)) return false;
    if (orgTypes.size > 0 && !orgTypes.has(r.org_type)) return false;
    if (q && !r.search_key.includes(q)) return false;
    // Statement-level groups ask "did this org report something matching X". A
    // responder with zero statements has nothing that can match, so it is excluded
    // exactly like an org whose statements all miss: filtering by district answers
    // "who reported in Rasuwa", and "nobody reported anything" is correctly "no". The
    // org is never hidden by DEFAULT (see the unfiltered board and every visual test),
    // only by an active statement-level filter that is, by its own question, about
    // reported statements. AND between groups, OR within a group.
    if (districts.size > 0 && !r.statements.some((s) => statementMatchesDistricts(s, districts))) {
      return false;
    }
    if (
      verification.size > 0 &&
      !r.statements.some((s) => statementMatchesVerification(s, verification))
    ) {
      return false;
    }
    return true;
  });

  result = sortResponders(result, f.sort);
  return result;
}

function latestOf(r: Responder): string {
  let latest = "";
  for (const s of r.statements) {
    const d = s.happened_on ?? s.datum.retrieved_at ?? "";
    if (d > latest) latest = d;
  }
  return latest;
}

function sortResponders(responders: Responder[], sort: FilterState["sort"]): Responder[] {
  const copy = [...responders];
  switch (sort) {
    case "name":
      return copy.sort((a, b) => a.name.localeCompare(b.name));
    case "fewest-data":
      // Orgs with no statement first, then fewer statements before more. This is a
      // completeness ordering, never an evidence-grade ordering: it never looks at
      // datum.verification. See filter.test.ts, "offers no sort by evidence grade".
      return copy.sort((a, b) => a.statements.length - b.statements.length || a.name.localeCompare(b.name));
    case "latest":
    default:
      // Most recently reported first. Orgs with no statement have no date and sort
      // last, but they are never hidden or dropped: they simply have nothing to be
      // "latest" about.
      return copy.sort((a, b) => {
        const la = latestOf(a);
        const lb = latestOf(b);
        if (la === lb) return a.name.localeCompare(b.name);
        if (la === "") return 1;
        if (lb === "") return -1;
        return la < lb ? 1 : -1;
      });
  }
}

// ---------------------------------------------------------------------------
// Chronological view
// ---------------------------------------------------------------------------

export function flattenStatements(responders: Responder[]): (Statement & { org: Responder })[] {
  const out: (Statement & { org: Responder })[] = [];
  for (const r of responders) {
    for (const s of r.statements) out.push({ ...s, org: r });
  }
  out.sort((a, b) => {
    const da = a.happened_on ?? a.datum.retrieved_at ?? "";
    const db = b.happened_on ?? b.datum.retrieved_at ?? "";
    return da < db ? 1 : da > db ? -1 : 0;
  });
  return out;
}

// ---------------------------------------------------------------------------
// Facets, recomputed against the currently filtered set so counts stay honest.
// ---------------------------------------------------------------------------

export function countFacets(responders: Responder[]): BoardData["facets"] {
  const districtOrgs = new Map<string, Set<string>>();
  const districtNames = new Map<string, string>();
  const noLocation = new Set<string>();
  const verificationOrgs = new Map<string, Set<string>>();
  const hqCounts = { local: 0, international: 0 };
  const orgTypeCounts = new Map<string, number>();

  for (const r of responders) {
    const key = r.org_id ?? r.org_name_raw;
    if (r.is_local) hqCounts.local += 1;
    else hqCounts.international += 1;
    orgTypeCounts.set(r.org_type, (orgTypeCounts.get(r.org_type) ?? 0) + 1);

    for (const s of r.statements) {
      if (s.districts.length === 0) noLocation.add(key);
      for (const d of s.districts) {
        districtNames.set(d.code, d.name);
        if (!districtOrgs.has(d.code)) districtOrgs.set(d.code, new Set());
        districtOrgs.get(d.code)!.add(key);
      }
      const v = s.datum.verification;
      if (!verificationOrgs.has(v)) verificationOrgs.set(v, new Set());
      verificationOrgs.get(v)!.add(key);
    }
  }

  const districts = [...districtOrgs.entries()]
    .map(([code, orgs]) => ({ key: code, label_key: districtNames.get(code) ?? code, count: orgs.size }))
    .sort((a, b) => b.count - a.count || a.label_key.localeCompare(b.label_key));
  districts.push({ key: "none", label_key: "none", count: noLocation.size });

  return {
    districts,
    hq: [
      { key: "local", label_key: "hq.local", count: hqCounts.local },
      { key: "international", label_key: "hq.international", count: hqCounts.international },
    ],
    orgType: [...orgTypeCounts.entries()]
      .map(([key, count]) => ({ key, label_key: `orgType.${key}`, count }))
      .sort((a, b) => a.key.localeCompare(b.key)),
    verification: (
      ["register_confirmed", "externally_audited", "self_reported", "third_party_reported", "unverified"] as const
    ).map((v) => ({ key: v, label_key: `verification.${v}`, count: verificationOrgs.get(v)?.size ?? 0 })),
  };
}

// Re-exported so components never need to know Datum lives in ./types too.
export type { Datum };
