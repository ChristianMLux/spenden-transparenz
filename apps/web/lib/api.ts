// Created by WP0. Owner from WP3 onward. WP1 and WP2 import from here and never edit it.
//
// Everything is read at build time from the research artefacts at the repository root.
// There is no request-time fetching anywhere in this app: the board and every org page
// are prerendered, and their data travels in the RSC payload.
//
// WP3 replaces the file reads with the live API behind SPENDEN_API_URL, keeps this as
// the fallback, adds zod validation and wraps each loader in `use cache` + `cacheTag`.
import { resolveDistrict } from "./districts";
import { readRepoJson } from "./repo-data";
import type {
  AmountBasis,
  BoardData,
  Correction,
  Crisis,
  Datum,
  DistrictRef,
  Facet,
  GapReason,
  OrgDetail,
  OrgType,
  Registration,
  Responder,
  SourceEntry,
  Statement,
  Verification,
} from "./types";

// ---------------------------------------------------------------------------
// Raw shapes of orgs-nepal-2026.json. Deliberately loose: this is foreign data.
// ---------------------------------------------------------------------------

interface RawDatum {
  value?: unknown;
  source_url?: string | null;
  retrieved_at?: string | null;
  verification?: string | null;
  quote?: string | null;
  note?: string | null;
}

interface RawResponse {
  what: string;
  where?: string[] | null;
  date?: string | null;
  amount?: number | null;
  currency?: string | null;
  source_url?: string | null;
  quote?: string | null;
  retrieved_at?: string | null;
  verification?: string | null;
  note?: string | null;
}

interface RawRegistration {
  registry: string;
  identifier?: string | null;
  url?: string | null;
  status?: string | null;
  retrieved_at?: string | null;
  verification?: string | null;
  note?: string | null;
}

interface RawOrg {
  org_id: string;
  names: {
    common: string;
    legal?: RawDatum;
    local_script?: RawDatum;
    aliases?: string[];
  };
  org_type: string;
  hq: { country: string; city?: string | null; source_url?: string | null };
  website?: string | null;
  registrations: RawRegistration[];
  nepal_presence: {
    since_year?: RawDatum;
    mode?: RawDatum;
    staff_count?: RawDatum;
    partners?: RawDatum[];
  };
  current_response?: RawResponse[];
  financial_transparency: {
    annual_report?: {
      available?: boolean | null;
      url?: string | null;
      fiscal_year?: string | number | null;
      fiscal_year_end?: string | null;
      retrieved_at?: string | null;
    };
    audited_financials?: RawDatum;
    iati_publisher?: {
      is_publisher?: boolean | null;
      publisher_ref?: string | null;
      source_url?: string | null;
      retrieved_at?: string | null;
    };
    income?: RawDatum & { currency?: string | null; fiscal_year?: string | number | null; scope?: string | null };
    expenditure?: RawDatum & { currency?: string | null; fiscal_year?: string | number | null; scope?: string | null };
    program_ratio?: RawDatum;
  };
  warnings?: { type: string; source_url?: string | null; date?: string | null; note?: string | null; retrieved_at?: string | null }[];
  data_gaps?: string[];
  research_notes?: string | null;
  last_updated: string;
}

interface RawDataset {
  generated_at: string;
  orgs: RawOrg[];
}

interface RawDisasterFile {
  retrieved_at: string;
  source: string;
  disaster: { url: string; title: string; disaster_id: string };
}

const DATASET = readRepoJson<RawDataset>("orgs-nepal-2026.json");
const DISASTER = readRepoJson<RawDisasterFile>("data/raw/reliefweb/disaster_updates.json");

// ---------------------------------------------------------------------------
// Provenance
// ---------------------------------------------------------------------------

const VERIFICATIONS: readonly Verification[] = [
  "register_confirmed",
  "externally_audited",
  "self_reported",
  "third_party_reported",
  "unverified",
];

const ORG_TYPES: readonly OrgType[] = [
  "un_agency",
  "red_cross_movement",
  "ingo",
  "national_ngo",
  "community_org",
  "diaspora_charity",
  "foundation",
  "government",
  "platform",
  "alliance",
  "unknown",
];

function verificationOf(raw: string | null | undefined): Verification {
  return VERIFICATIONS.includes(raw as Verification) ? (raw as Verification) : "unverified";
}

function orgTypeOf(raw: string): OrgType {
  return ORG_TYPES.includes(raw as OrgType) ? (raw as OrgType) : "unknown";
}

function publisherOf(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

// TODO(backend v0.2): delete this and read org_datum.gap_reason. Until the schema ships
// the field, the reason is inferred from the research note, which is the only place the
// distinction currently exists. Three very different honesty statements would otherwise
// render identically.
function gapReasonOf(note: string | null): GapReason {
  if (!note || note.trim() === "") return "not_searched";
  if (/unreachable|not reachable|nicht erreichbar|timed? out|HTTP 4\d\d|HTTP 5\d\d/i.test(note)) {
    return "source_unreachable";
  }
  if (/not published|does not publish|nicht ver(oe|ö)ffentlicht|not public|no public register/i.test(note)) {
    return "not_public";
  }
  return "searched_not_found";
}

function toDatum<T>(raw: RawDatum | undefined, fallbackRetrievedAt: string | null = null): Datum<T> {
  const value = (raw?.value ?? null) as T | null;
  const note = raw?.note ?? null;
  const source_url = raw?.source_url ?? null;
  return {
    value,
    is_gap: value === null,
    source_url,
    publisher: publisherOf(source_url),
    retrieved_at: raw?.retrieved_at ?? fallbackRetrievedAt,
    published_at: null,
    verification: verificationOf(raw?.verification),
    quote: raw?.quote ?? null,
    note,
    gap_reason: value === null ? gapReasonOf(note) : null,
  };
}

// ---------------------------------------------------------------------------
// Amounts
//
// The basis is read only from the activity sentence, never from the research note: notes
// routinely say "not confirmed disbursed", and matching that would label a pledge as a
// payment. Checks run weakest claim first, so an ambiguous sentence gets the weaker
// label. Anything unrecognised stays "reported", which claims nothing beyond the figure
// having been published.
// ---------------------------------------------------------------------------

const BASIS_PATTERNS: [AmountBasis, RegExp][] = [
  ["appeal", /\bappeal\b|\bappell\b|\bspendenaufruf\b/i],
  ["pledged", /\bannounc\w*\b|\bpledg\w*\b|\bzugesagt\b|\bangek(ue|ü)ndigt\b|\bcommitted\b/i],
  ["raised", /\braised\b|\bgesammelt\b|\bdonations? received\b/i],
  ["released", /\breleased\b|\ballocat\w*\b|\bprovided\b|\bfreigegeben\b|\bbereitgestellt\b/i],
  ["disbursed", /\bdisbursed\b|\bausgezahlt\b|\bpaid out\b/i],
];

function amountBasisOf(activity: string): AmountBasis {
  for (const [basis, pattern] of BASIS_PATTERNS) {
    if (pattern.test(activity)) return basis;
  }
  return "reported";
}

// ---------------------------------------------------------------------------
// Search key
// ---------------------------------------------------------------------------

const fold = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/\s+/g, " ")
    .trim();

// ---------------------------------------------------------------------------
// Mapping
// ---------------------------------------------------------------------------

function toStatement(orgId: string, index: number, raw: RawResponse): Statement {
  const districts: DistrictRef[] = [];
  const seen = new Set<string>();
  for (const where of raw.where ?? []) {
    const district = resolveDistrict(where);
    // An unresolvable location becomes no district at all. It never becomes a guess and
    // it never silently drops the statement: "no location stated" is its own filter.
    if (district && !seen.has(district.code)) {
      seen.add(district.code);
      districts.push(district);
    }
  }

  return {
    id: `${orgId}#${index}`,
    districts,
    happened_on: raw.date ?? null,
    amount: raw.amount ?? null,
    currency: raw.currency ?? null,
    amount_basis: raw.amount === null || raw.amount === undefined ? null : amountBasisOf(raw.what),
    datum: {
      // The activity sentence IS the value, so a sentence cannot exist without its source.
      value: raw.what,
      is_gap: false,
      source_url: raw.source_url ?? null,
      publisher: publisherOf(raw.source_url ?? null),
      retrieved_at: raw.retrieved_at ?? null,
      published_at: raw.date ?? null,
      verification: verificationOf(raw.verification),
      quote: raw.quote ?? null,
      note: raw.note ?? null,
      gap_reason: null,
    },
  };
}

function toResponder(raw: RawOrg): Responder {
  const aliases = raw.names.aliases ?? [];
  return {
    org_id: raw.org_id,
    org_name_raw: raw.names.common,
    name: raw.names.common,
    local_script: (raw.names.local_script?.value as string | undefined) ?? null,
    aliases,
    org_type: orgTypeOf(raw.org_type),
    hq_country: raw.hq.country,
    is_local: raw.hq.country === "NP",
    // Folded once at build. The filter compares against this and never re-normalises.
    search_key: fold([raw.names.common, ...aliases].join(" ")),
    statements: (raw.current_response ?? []).map((r, i) => toStatement(raw.org_id, i, r)),
  };
}

function toRegistration(raw: RawRegistration): Registration {
  const datum = toDatum<string>(
    {
      value: raw.identifier ?? null,
      source_url: raw.url ?? null,
      retrieved_at: raw.retrieved_at ?? null,
      verification: raw.verification ?? null,
      note: raw.note ?? null,
    },
    raw.retrieved_at ?? null,
  );
  return { registry: raw.registry, datum, register_url: raw.url ?? null, status: raw.status ?? null };
}

function toOrgDetail(raw: RawOrg): OrgDetail {
  const ft = raw.financial_transparency;
  const annualReport = ft.annual_report;
  const iati = ft.iati_publisher;

  return {
    org_id: raw.org_id,
    name: raw.names.common,
    local_script: toDatum<string>(raw.names.local_script, raw.last_updated),
    legal_name: toDatum<string>(raw.names.legal, raw.last_updated),
    aliases: raw.names.aliases ?? [],
    org_type: orgTypeOf(raw.org_type),
    hq_country: raw.hq.country,
    hq_city: raw.hq.city ?? null,
    website: raw.website ?? null,
    last_updated: raw.last_updated,
    statements: (raw.current_response ?? []).map((r, i) => toStatement(raw.org_id, i, r)),
    presence: {
      since_year: toDatum<number>(raw.nepal_presence.since_year, raw.last_updated),
      mode: toDatum<string>(raw.nepal_presence.mode, raw.last_updated),
      staff_count: toDatum<number>(raw.nepal_presence.staff_count, raw.last_updated),
      partners: (raw.nepal_presence.partners ?? []).map((p) => toDatum<string>(p, raw.last_updated)),
    },
    registrations: raw.registrations.map(toRegistration),
    financials: {
      annual_report: toDatum<string>(
        {
          value: annualReport?.available ? (annualReport.url ?? null) : null,
          source_url: annualReport?.url ?? null,
          retrieved_at: annualReport?.retrieved_at ?? null,
          verification: annualReport?.available ? "self_reported" : "unverified",
          note: annualReport?.available ? null : "Kein Jahresbericht gefunden.",
        },
        raw.last_updated,
      ),
      audited: toDatum<string>(ft.audited_financials, raw.last_updated),
      iati_ref: toDatum<string>(
        {
          value: iati?.publisher_ref ?? null,
          source_url: iati?.source_url ?? null,
          retrieved_at: iati?.retrieved_at ?? null,
          verification: iati?.publisher_ref ? "register_confirmed" : "unverified",
          note: iati?.publisher_ref ? null : null,
        },
        raw.last_updated,
      ),
      income: toDatum<number>(ft.income, raw.last_updated),
      expenditure: toDatum<number>(ft.expenditure, raw.last_updated),
      program_ratio: toDatum<number>(ft.program_ratio, raw.last_updated),
      currency: (ft.income?.currency ?? ft.expenditure?.currency) ?? null,
      fiscal_year: String(ft.income?.fiscal_year ?? ft.expenditure?.fiscal_year ?? "") || null,
      scope: (ft.income?.scope ?? ft.expenditure?.scope) ?? null,
    },
    warnings: (raw.warnings ?? []).map((w) => ({
      type: w.type,
      datum: toDatum<string>(
        {
          value: w.note ?? w.type,
          source_url: w.source_url ?? null,
          retrieved_at: w.retrieved_at ?? null,
          verification: "third_party_reported",
          note: w.note ?? null,
        },
        raw.last_updated,
      ),
    })),
    data_gaps: raw.data_gaps ?? [],
    research_notes: raw.research_notes ?? null,
  };
}

// ---------------------------------------------------------------------------
// Facets
//
// Counts are organisation counts, because the list being filtered is a list of
// organisations and a facet count should predict the size of the result.
//
// A closed, small taxonomy lists every value even at zero, so a reader can see that a
// grade exists and nothing matched it. Districts list only the values that occur: three
// filled rows out of 77 would read as "nothing happened", which is the misreading the
// spec exists to avoid.
// ---------------------------------------------------------------------------

const CRISES: Record<string, Crisis> = {
  "nepal-flut-2026": {
    glide_id: "ff-2026-000162-npl",
    slug: "nepal-flut-2026",
    name_de: "Nepal: Sturzfluten, August 2026",
    name_en: "Nepal: Flash Floods, August 2026",
    started_on: "2026-08-26",
    source_url: DISASTER.disaster.url,
  },
};

function buildFacets(responders: Responder[]): BoardData["facets"] {
  const districtOrgs = new Map<string, Set<string>>();
  const districtNames = new Map<string, string>();
  const noLocation = new Set<string>();
  const verificationOrgs = new Map<string, Set<string>>();

  for (const r of responders) {
    const key = r.org_id ?? r.org_name_raw;
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

  const districts: Facet[] = [...districtOrgs.entries()]
    .map(([code, orgs]) => ({ key: code, label_key: districtNames.get(code) ?? code, count: orgs.size }))
    .sort((a, b) => b.count - a.count || a.label_key.localeCompare(b.label_key));
  districts.push({ key: "none", label_key: "none", count: noLocation.size });

  const orgTypeCounts = new Map<string, number>();
  for (const r of responders) orgTypeCounts.set(r.org_type, (orgTypeCounts.get(r.org_type) ?? 0) + 1);

  return {
    districts,
    hq: [
      { key: "local", label_key: "hq.local", count: responders.filter((r) => r.is_local).length },
      {
        key: "international",
        label_key: "hq.international",
        count: responders.filter((r) => !r.is_local).length,
      },
    ],
    orgType: ORG_TYPES.map((t) => ({
      key: t,
      label_key: `orgType.${t}`,
      count: orgTypeCounts.get(t) ?? 0,
    })),
    verification: VERIFICATIONS.map((v) => ({
      key: v,
      label_key: `verification.${v}`,
      count: verificationOrgs.get(v)?.size ?? 0,
    })),
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function getCrisis(slug: string): Promise<Crisis> {
  const crisis = CRISES[slug];
  if (!crisis) throw new Error(`Unknown crisis: ${slug}`);
  return crisis;
}

export async function getBoard(slug: string): Promise<BoardData> {
  const crisis = await getCrisis(slug);
  const responders = DATASET.orgs.map(toResponder);

  const districtCodes = new Set<string>();
  let statements = 0;
  for (const r of responders) {
    statements += r.statements.length;
    for (const s of r.statements) for (const d of s.districts) districtCodes.add(d.code);
  }

  return {
    crisis,
    generated_at: DISASTER.retrieved_at,
    responders,
    facets: buildFacets(responders),
    counts: {
      orgs: responders.length,
      statements,
      districts: districtCodes.size,
      orgsWithoutResponse: responders.filter((r) => r.statements.length === 0).length,
    },
  };
}

export async function listOrgIds(): Promise<string[]> {
  return DATASET.orgs.map((o) => o.org_id);
}

export async function getOrg(orgId: string): Promise<OrgDetail> {
  const raw = DATASET.orgs.find((o) => o.org_id === orgId);
  if (!raw) throw new Error(`Unknown organisation: ${orgId}`);
  return toOrgDetail(raw);
}

export async function getFreshness(): Promise<{ retrieved_at: string; source: string }> {
  return { retrieved_at: DISASTER.retrieved_at, source: DISASTER.source };
}

export async function getSources(): Promise<SourceEntry[]> {
  // WP3 owns the real catalogue. Keeping the shape here so /quellen can be built against it.
  return [
    {
      key: "reliefweb",
      name: "ReliefWeb",
      url: "https://reliefweb.int/",
      licence: "ReliefWeb terms of use",
      retrieved_at: DISASTER.retrieved_at.slice(0, 10),
    },
    {
      key: "hapi",
      name: "OCHA Humanitarian API (admin boundaries)",
      url: "https://hapi.humdata.org/",
      licence: "CC BY-IGO",
      retrieved_at: "2026-08-28",
    },
  ];
}

export async function getCorrections(): Promise<Correction[]> {
  // WP3 seeds the two real sampling errors here on day one. An empty corrections page
  // would be the least credible page on the site.
  return [];
}
