// Owned by WP3 (from WP0's naive scaffold onward). WP1 and WP2 import from here and
// never edit it: a rename here breaks two agents mid-flight, so only add to this file,
// never rename the exported signatures listed as "Locked interfaces" in the plan.
//
// Two data sources, one contract. When SPENDEN_API_URL is set, every loader below reads
// from the live FastAPI backend and validates the response against the OpenAPI contract
// (apps/api/openapi.json) with zod. When it is unset, every loader reads the research
// artefacts at the repository root (orgs-nepal-2026.json, disaster_updates.json) and
// validates them the same way. The JSON fallback is not scaffolding for the live API to
// replace: it stays in the code permanently, because a research pass that never gets a
// backend deploy should still render a working site.
//
// Every record read from either source is validated by a zod schema before it reaches a
// component. A malformed record fails the build (or the request, in the live-API path)
// with a path-qualified error instead of quietly rendering `undefined`.
import { cacheLife, cacheTag } from "next/cache";
import { z } from "zod";
import { resolveDistrict } from "./districts";
import { readDisaster, readDonationChannels, readOrgs } from "./repo-data";
import type {
  AmountBasis,
  BoardData,
  Correction,
  Crisis,
  Datum,
  DistrictRef,
  DonationChannel,
  DonationChannelType,
  DonationLink,
  Facet,
  GapReason,
  GovernmentFund,
  OrgDetail,
  OrgType,
  Registration,
  Responder,
  SourceEntry,
  Statement,
  Verification,
} from "./types";

// ---------------------------------------------------------------------------
// gap_reason: the honesty distinction the rest of this file is built around.
// ---------------------------------------------------------------------------

const GAP_REASONS = ["not_searched", "searched_not_found", "source_unreachable", "not_public"] as const;

function isGapReason(value: unknown): value is GapReason {
  return (GAP_REASONS as readonly unknown[]).includes(value);
}

// ---------------------------------------------------------------------------
// Raw shapes of orgs-nepal-2026.json, validated with zod.
//
// Schema v0.2: every datum-shaped object in the source file now carries its own
// gap_reason when its value is null. There used to be a fallback here that guessed the
// reason from the free-text research note (unreachable / not public / else) - that
// guess was wrong whenever a note was phrased in a way the three regexes did not
// anticipate (see lib/api.test.ts for a real example the old derivation got wrong). The
// backend now ships the real field, so this file only ever reads it.
// ---------------------------------------------------------------------------

const zGapAwareRefinement = (valueKey: "value" | "identifier") => (obj: Record<string, unknown>) => {
  const value = obj[valueKey];
  if (value !== null && value !== undefined) return true;
  return isGapReason(obj.gap_reason);
};

const RawDatumSchema = z
  .object({
    value: z.unknown().optional(),
    source_url: z.string().nullable().optional(),
    retrieved_at: z.string().nullable().optional(),
    verification: z.string().nullable().optional(),
    quote: z.string().nullable().optional(),
    note: z.string().nullable().optional(),
    gap_reason: z.enum(GAP_REASONS).nullable().optional(),
  })
  .refine(zGapAwareRefinement("value"), {
    message: "a gap (value: null) must carry one of the four gap_reason values",
  });

const RawFinancialDatumSchema = z
  .object({
    value: z.unknown().optional(),
    currency: z.string().nullable().optional(),
    fiscal_year: z.union([z.string(), z.number()]).nullable().optional(),
    scope: z.string().nullable().optional(),
    source_url: z.string().nullable().optional(),
    retrieved_at: z.string().nullable().optional(),
    verification: z.string().nullable().optional(),
    quote: z.string().nullable().optional(),
    note: z.string().nullable().optional(),
    gap_reason: z.enum(GAP_REASONS).nullable().optional(),
  })
  .refine(zGapAwareRefinement("value"), {
    message: "a gap (value: null) must carry one of the four gap_reason values",
  });

const RawResponseSchema = z.object({
  // The activity sentence IS the value: a statement cannot exist without one.
  what: z.string().min(1),
  where: z.array(z.string()).nullable().optional(),
  date: z.string().nullable().optional(),
  amount: z.number().nullable().optional(),
  currency: z.string().nullable().optional(),
  source_url: z.string().nullable().optional(),
  quote: z.string().nullable().optional(),
  retrieved_at: z.string().nullable().optional(),
  verification: z.string().nullable().optional(),
  note: z.string().nullable().optional(),
});

const RawRegistrationSchema = z
  .object({
    registry: z.string().min(1),
    identifier: z.string().nullable().optional(),
    url: z.string().nullable().optional(),
    status: z.string().nullable().optional(),
    retrieved_at: z.string().nullable().optional(),
    verification: z.string().nullable().optional(),
    note: z.string().nullable().optional(),
    gap_reason: z.enum(GAP_REASONS).nullable().optional(),
  })
  .refine(zGapAwareRefinement("identifier"), {
    message: "a registration with no identifier must carry one of the four gap_reason values",
  });

const RawOrgSchema = z.object({
  org_id: z.string().min(1),
  names: z.object({
    common: z.string().min(1),
    legal: RawDatumSchema.optional(),
    local_script: RawDatumSchema.optional(),
    aliases: z.array(z.string()).optional(),
  }),
  org_type: z.string().min(1),
  hq: z.object({
    country: z.string().min(1),
    city: z.string().nullable().optional(),
    source_url: z.string().nullable().optional(),
  }),
  website: z.string().nullable().optional(),
  registrations: z.array(RawRegistrationSchema),
  nepal_presence: z.object({
    since_year: RawDatumSchema.optional(),
    mode: RawDatumSchema.optional(),
    staff_count: RawDatumSchema.optional(),
    partners: z.array(RawDatumSchema).optional(),
  }),
  current_response: z.array(RawResponseSchema).optional(),
  financial_transparency: z.object({
    annual_report: z
      .object({
        available: z.boolean().nullable().optional(),
        url: z.string().nullable().optional(),
        fiscal_year: z.union([z.string(), z.number()]).nullable().optional(),
        fiscal_year_end: z.string().nullable().optional(),
        retrieved_at: z.string().nullable().optional(),
      })
      .optional(),
    audited_financials: RawDatumSchema.optional(),
    iati_publisher: z
      .object({
        is_publisher: z.boolean().nullable().optional(),
        publisher_ref: z.string().nullable().optional(),
        source_url: z.string().nullable().optional(),
        retrieved_at: z.string().nullable().optional(),
      })
      .optional(),
    income: RawFinancialDatumSchema.optional(),
    expenditure: RawFinancialDatumSchema.optional(),
    program_ratio: RawDatumSchema.optional(),
  }),
  warnings: z
    .array(
      z.object({
        type: z.string(),
        source_url: z.string().nullable().optional(),
        date: z.string().nullable().optional(),
        note: z.string().nullable().optional(),
        retrieved_at: z.string().nullable().optional(),
      }),
    )
    .optional(),
  data_gaps: z.array(z.string()).optional(),
  research_notes: z.string().nullable().optional(),
  last_updated: z.string().min(1),
});

const RawDatasetSchema = z.object({
  generated_at: z.string(),
  orgs: z.array(RawOrgSchema).min(1),
});

const RawDisasterFileSchema = z.object({
  retrieved_at: z.string(),
  source: z.string(),
  disaster: z.object({
    url: z.string(),
    title: z.string(),
    disaster_id: z.string(),
  }),
});

// The official donation channel per organisation. Researched by hand into
// data/orgs/donation-channels.json; the API gains the field with schema v0.5, and
// donationFor() below is the single place that then has to change.
const CHANNEL_TYPES = ["donation_page", "platform_page", "bank_transfer_page"] as const;

const RawDonationEntrySchema = z.object({
  value: z.string().nullable(),
  channel_type: z.enum(CHANNEL_TYPES).nullable(),
  flood_specific: z.boolean().nullable(),
  source_url: z.string().nullable(),
  retrieved_at: z.string().nullable(),
  verification: z.string().nullable(),
  quote: z.string().nullable(),
  note: z.string().nullable(),
  gap_reason: z.string().nullable(),
});

const RawDonationFileSchema = z.object({
  generated_at: z.string(),
  rules: z.string().optional(),
  channels: z.record(z.string(), RawDonationEntrySchema),
  government_funds: z.array(
    RawDonationEntrySchema.extend({
      name: z.string(),
      // Absent in the file rather than null: a state relief fund is not a campaign
      // page for one flood. Defaulting here keeps the 44 organisation entries strict.
      flood_specific: z.boolean().nullable().default(null),
    }),
  ),
});

type RawDatum = z.infer<typeof RawDatumSchema>;
type RawRegistration = z.infer<typeof RawRegistrationSchema>;
type RawOrg = z.infer<typeof RawOrgSchema>;
type RawDataset = z.infer<typeof RawDatasetSchema>;
type RawDisasterFile = z.infer<typeof RawDisasterFileSchema>;

/** Exported only so lib/api.test.ts can prove a malformed record fails validation
 *  without needing its own fixture file. Not part of the locked interface. */
export { RawDatasetSchema };

let cachedDonations: z.infer<typeof RawDonationFileSchema> | null = null;
function donationFile(): z.infer<typeof RawDonationFileSchema> {
  if (!cachedDonations) {
    const parsed = RawDonationFileSchema.safeParse(readDonationChannels<unknown>());
    if (!parsed.success) {
      throw new Error(
        `donation-channels.json failed schema validation:\n${describeIssues(parsed.error)}`,
      );
    }
    cachedDonations = parsed.data;
  }
  return cachedDonations;
}

function describeIssues(error: z.ZodError): string {
  return error.issues.map((issue) => `  ${issue.path.join(".") || "(root)"}: ${issue.message}`).join("\n");
}

let cachedDataset: RawDataset | null = null;
function localDataset(): RawDataset {
  if (!cachedDataset) {
    const parsed = RawDatasetSchema.safeParse(readOrgs<unknown>());
    if (!parsed.success) {
      throw new Error(`orgs-nepal-2026.json failed schema validation:\n${describeIssues(parsed.error)}`);
    }
    cachedDataset = parsed.data;
  }
  return cachedDataset;
}

let cachedDisaster: RawDisasterFile | null = null;
function localDisaster(): RawDisasterFile {
  if (!cachedDisaster) {
    const parsed = RawDisasterFileSchema.safeParse(readDisaster<unknown>());
    if (!parsed.success) {
      throw new Error(`disaster-updates.json failed schema validation:\n${describeIssues(parsed.error)}`);
    }
    cachedDisaster = parsed.data;
  }
  return cachedDisaster;
}

// ---------------------------------------------------------------------------
// The live API. SPENDEN_API_URL is unset in every environment this session (the
// backend has not been deployed yet - see PO-5 in the plan), so this branch is
// implemented against the OpenAPI contract at apps/api/openapi.json but is not
// exercised end to end by these tests. The JSON-fallback branch below it is what every
// test and every build in this repository actually runs, and it stays the default.
// ---------------------------------------------------------------------------

const LIVE_API_URL = process.env.SPENDEN_API_URL;

const ApiVerificationSchema = z.enum([
  "self_reported",
  "register_confirmed",
  "externally_audited",
  "third_party_reported",
  "unverified",
]);

const ApiDatumSchema = z.object({
  value: z.unknown().nullable().optional(),
  is_gap: z.boolean(),
  source_url: z.string().nullable().optional(),
  retrieved_at: z.string().nullable().optional(),
  verification: ApiVerificationSchema,
  quote: z.string().nullable().optional(),
  note: z.string().nullable().optional(),
  gap_reason: z.enum(GAP_REASONS).nullable().optional(),
  currency: z.string().nullable().optional(),
  fiscal_year: z.string().nullable().optional(),
  scope: z.string().nullable().optional(),
});

const ApiSourceRefSchema = z.object({
  url: z.string(),
  publisher: z.string().nullable().optional(),
  published_at: z.string().nullable().optional(),
  verification: ApiVerificationSchema,
});

const ApiDistrictRefSchema = z.object({ code: z.string(), name: z.string() });

const ApiStatementSchema = z.object({
  id: z.union([z.string(), z.number()]),
  activity: z.string(),
  activity_type: z.string(),
  quote: z.string(),
  amount: z.string().nullable().optional(),
  amount_basis: z.string().optional(),
  currency: z.string().nullable().optional(),
  districts: z.array(ApiDistrictRefSchema).optional(),
  happened_on: z.string().nullable().optional(),
  source: ApiSourceRefSchema,
});

const ApiOrgRefSchema = z.object({
  org_id: z.string(),
  name_common: z.string(),
  org_type: z.string(),
  hq_country: z.string().nullable().optional(),
  website: z.string().nullable().optional(),
});

const ApiResponderItemSchema = z.object({
  org: ApiOrgRefSchema.nullable().optional(),
  org_name_raw: z.string(),
  statements: z.array(ApiStatementSchema).optional(),
  counts: z.object({ statements: z.number(), districts: z.number() }),
});

const ApiDisasterSchema = z.object({
  glide_id: z.string(),
  name: z.string(),
  is_active: z.boolean(),
  started_on: z.string().nullable().optional(),
  source_url: z.string().nullable().optional(),
});

const ApiSourceOutSchema = z.object({
  id: z.string(),
  name: z.string(),
  url: z.string(),
  licence: z.string().nullable().optional(),
  retrieved_at: z.string().nullable().optional(),
  default_verification: ApiVerificationSchema,
});

const ApiFreshnessOutSchema = z.object({
  generated_at: z.string(),
  jobs: z.array(z.object({ job: z.string() })).optional(),
});

const ApiRegistrationOutSchema = z.object({
  registry: z.string(),
  identifier: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  status: z.string().nullable().optional(),
  retrieved_at: z.string().nullable().optional(),
  verification: ApiVerificationSchema,
  note: z.string().nullable().optional(),
  gap_reason: z.enum(GAP_REASONS).nullable().optional(),
});

const ApiWarningOutSchema = z.object({
  type: z.string(),
  source_url: z.string(),
  note: z.string(),
  retrieved_at: z.string().nullable().optional(),
});

const ApiOrgDetailSchema = z.object({
  org_id: z.string(),
  name_common: z.string(),
  org_type: z.string(),
  aliases: z.array(z.string()).optional(),
  hq_country: z.string().nullable().optional(),
  hq_city: z.string().nullable().optional(),
  website: z.string().nullable().optional(),
  last_updated: z.string().nullable().optional(),
  statements: z.array(ApiStatementSchema).optional(),
  registrations: z.array(ApiRegistrationOutSchema).optional(),
  warnings: z.array(ApiWarningOutSchema).optional(),
  data_gaps: z.array(z.string()).optional(),
  research_notes: z.string().nullable().optional(),
  data: z.record(z.string(), ApiDatumSchema),
});

async function fetchLive<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${LIVE_API_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Live API request failed: GET ${path} -> ${response.status} ${response.statusText}`);
  }
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) {
    throw new Error(`Live API response for ${path} failed schema validation:\n${describeIssues(parsed.error)}`);
  }
  return parsed.data;
}

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

function orgTypeOf(raw: string | null | undefined): OrgType {
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

function toDonationChannel(
  raw: z.infer<typeof RawDonationEntrySchema> | undefined,
): DonationChannel {
  // An organisation absent from the file was never searched, which is a different
  // statement from "searched and found nothing" and has to survive as one.
  if (!raw) {
    return {
      url: null,
      channel_type: null,
      flood_specific: null,
      source_url: null,
      publisher: null,
      retrieved_at: null,
      verification: "unverified",
      quote: null,
      note: null,
      gap_reason: "not_searched",
    };
  }
  return {
    url: raw.value,
    channel_type: raw.channel_type as DonationChannelType | null,
    flood_specific: raw.flood_specific,
    source_url: raw.source_url,
    publisher: publisherOf(raw.value ?? raw.source_url),
    retrieved_at: raw.retrieved_at,
    verification: verificationOf(raw.verification),
    quote: raw.quote,
    note: raw.note,
    gap_reason: isGapReason(raw.gap_reason)
      ? raw.gap_reason
      : raw.value
        ? null
        : "searched_not_found",
  };
}

/** The one seam the live API replaces when schema v0.5 ships the field. */
function donationFor(orgId: string | null): DonationChannel {
  return toDonationChannel(orgId ? donationFile().channels[orgId] : undefined);
}

/** The board's five fields. See DonationLink for why the rest does not travel. */
function donationLinkFor(orgId: string | null): DonationLink {
  const full = donationFor(orgId);
  return {
    url: full.url,
    retrieved_at: full.retrieved_at,
    verification: full.verification,
    gap_reason: full.gap_reason,
  };
}

function governmentFunds(): GovernmentFund[] {
  return donationFile().government_funds.map((fund) => ({
    ...toDonationChannel(fund),
    name: fund.name,
  }));
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
    // Read straight from the source. RawDatumSchema's refinement already guarantees
    // this is one of the four values whenever value is null - there is nothing left to
    // guess here.
    gap_reason: value === null ? (raw?.gap_reason ?? null) : null,
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
// Mapping: local JSON fallback -> the app's types
// ---------------------------------------------------------------------------

function toStatement(orgId: string, index: number, raw: z.infer<typeof RawResponseSchema>): Statement {
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
    donation: donationLinkFor(raw.org_id),
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
      gap_reason: raw.gap_reason ?? null,
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
    donation: donationFor(raw.org_id),
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
          // A real search happened (annual_report.available === false is itself the
          // search result), so a missing report is searched_not_found, not not_searched.
          gap_reason: annualReport?.available ? null : "searched_not_found",
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
          note: null,
          gap_reason: iati?.publisher_ref ? null : "searched_not_found",
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
// Mapping: live API -> the app's types
// ---------------------------------------------------------------------------

function apiDatumToLocal<T>(raw: z.infer<typeof ApiDatumSchema> | undefined): Datum<T> {
  if (!raw) {
    return {
      value: null,
      is_gap: true,
      source_url: null,
      publisher: null,
      retrieved_at: null,
      published_at: null,
      verification: "unverified",
      quote: null,
      note: null,
      gap_reason: "not_searched",
    };
  }
  const source_url = raw.source_url ?? null;
  return {
    value: (raw.value ?? null) as T | null,
    is_gap: raw.is_gap,
    source_url,
    publisher: publisherOf(source_url),
    retrieved_at: raw.retrieved_at ?? null,
    published_at: null,
    verification: raw.verification,
    quote: raw.quote ?? null,
    note: raw.note ?? null,
    gap_reason: raw.is_gap ? (raw.gap_reason ?? "not_searched") : null,
  };
}

function apiStatementToLocal(raw: z.infer<typeof ApiStatementSchema>): Statement {
  return {
    id: String(raw.id),
    districts: (raw.districts ?? []).map((d) => ({ code: d.code, name: d.name })),
    happened_on: raw.happened_on ?? null,
    amount: raw.amount !== null && raw.amount !== undefined && raw.amount !== "" ? Number(raw.amount) : null,
    currency: raw.currency ?? null,
    amount_basis: (raw.amount_basis as AmountBasis | undefined) ?? null,
    datum: {
      value: raw.activity,
      is_gap: false,
      source_url: raw.source.url,
      publisher: raw.source.publisher ?? publisherOf(raw.source.url),
      retrieved_at: null,
      published_at: raw.source.published_at ?? null,
      verification: raw.source.verification,
      quote: raw.quote,
      note: null,
      gap_reason: null,
    },
  };
}

function apiResponderToLocal(raw: z.infer<typeof ApiResponderItemSchema>): Responder {
  const org = raw.org ?? null;
  const name = org?.name_common ?? raw.org_name_raw;
  return {
    org_id: org?.org_id ?? null,
    org_name_raw: raw.org_name_raw,
    name,
    // The live responders list does not carry a local-script name or an alias list at
    // this level (only /v1/orgs/{org_id} does); the board renders from the Latin name.
    local_script: null,
    aliases: [],
    org_type: orgTypeOf(org?.org_type),
    hq_country: org?.hq_country ?? "unknown",
    is_local: org?.hq_country === "NP",
    search_key: fold(name),
    statements: (raw.statements ?? []).map(apiStatementToLocal),
    // Until the API carries the field (schema v0.5) both paths read the same file.
    donation: donationLinkFor(org?.org_id ?? null),
  };
}

function apiOrgDetailToLocal(raw: z.infer<typeof ApiOrgDetailSchema>): OrgDetail {
  const data = raw.data;
  const pick = <T>(path: string): Datum<T> => apiDatumToLocal<T>(data[path]);
  const income = data["financial_transparency.income"];
  const expenditure = data["financial_transparency.expenditure"];

  return {
    org_id: raw.org_id,
    name: raw.name_common,
    // Same seam as the board: the API carries the field from schema v0.5.
    donation: donationFor(raw.org_id),
    local_script: pick<string>("names.local_script"),
    legal_name: pick<string>("names.legal"),
    aliases: raw.aliases ?? [],
    org_type: orgTypeOf(raw.org_type),
    hq_country: raw.hq_country ?? "unknown",
    hq_city: raw.hq_city ?? null,
    website: raw.website ?? null,
    last_updated: raw.last_updated ?? "",
    statements: (raw.statements ?? []).map(apiStatementToLocal),
    presence: {
      since_year: pick<number>("nepal_presence.since_year"),
      mode: pick<string>("nepal_presence.mode"),
      staff_count: pick<number>("nepal_presence.staff_count"),
      // The path-keyed data map has no array convention for a repeated field; the
      // contract does not expose partners distinctly yet.
      partners: [],
    },
    registrations: (raw.registrations ?? []).map((r) => ({
      registry: r.registry,
      datum: apiDatumToLocal<string>({
        value: r.identifier ?? null,
        is_gap: r.identifier === null || r.identifier === undefined,
        source_url: r.url ?? null,
        retrieved_at: r.retrieved_at ?? null,
        verification: r.verification,
        quote: null,
        note: r.note ?? null,
        gap_reason: r.gap_reason ?? null,
      }),
      register_url: r.url ?? null,
      status: r.status ?? null,
    })),
    financials: {
      annual_report: pick<string>("financial_transparency.annual_report"),
      audited: pick<string>("financial_transparency.audited_financials"),
      iati_ref: pick<string>("financial_transparency.iati_ref"),
      income: pick<number>("financial_transparency.income"),
      expenditure: pick<number>("financial_transparency.expenditure"),
      program_ratio: pick<number>("financial_transparency.program_ratio"),
      currency: income?.currency ?? expenditure?.currency ?? null,
      fiscal_year: income?.fiscal_year ?? expenditure?.fiscal_year ?? null,
      scope: income?.scope ?? expenditure?.scope ?? null,
    },
    warnings: (raw.warnings ?? []).map((w) => ({
      type: w.type,
      datum: apiDatumToLocal<string>({
        value: w.note,
        is_gap: false,
        source_url: w.source_url,
        retrieved_at: w.retrieved_at ?? null,
        verification: "third_party_reported",
        quote: null,
        note: w.note,
        gap_reason: null,
      }),
    })),
    data_gaps: raw.data_gaps ?? [],
    research_notes: raw.research_notes ?? null,
  };
}

// ---------------------------------------------------------------------------
// Crisis metadata
//
// name_de/name_en are this app's own i18n content, never the backend's: the API's
// DisasterOut carries a single `name`, not a locale pair. The live branch overlays only
// the fields the backend actually owns (started_on, source_url) onto the local record.
// ---------------------------------------------------------------------------

const CRISIS_META: Record<string, Omit<Crisis, "source_url">> = {
  "nepal-flut-2026": {
    glide_id: "ff-2026-000162-npl",
    slug: "nepal-flut-2026",
    name_de: "Nepal: Sturzfluten, August 2026",
    name_en: "Nepal: Flash Floods, August 2026",
    started_on: "2026-08-26",
  },
};

const DEFAULT_GLIDE_ID = CRISIS_META["nepal-flut-2026"]!.glide_id;

function localCrisisMeta(slug: string): Omit<Crisis, "source_url"> {
  const meta = CRISIS_META[slug];
  if (!meta) throw new Error(`Unknown crisis: ${slug}`);
  return meta;
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

function boardCounts(responders: Responder[]): BoardData["counts"] {
  const districtCodes = new Set<string>();
  let statements = 0;
  for (const r of responders) {
    statements += r.statements.length;
    for (const s of r.statements) for (const d of s.districts) districtCodes.add(d.code);
  }
  return {
    orgs: responders.length,
    statements,
    districts: districtCodes.size,
    orgsWithoutResponse: responders.filter((r) => r.statements.length === 0).length,
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function getCrisis(slug: string): Promise<Crisis> {
  "use cache";
  const local = localCrisisMeta(slug);
  cacheTag(`crisis:${local.glide_id}`);
  cacheLife("hours");

  if (!LIVE_API_URL) {
    return { ...local, source_url: localDisaster().disaster.url };
  }
  const live = await fetchLive(`/v1/disasters/${local.glide_id}`, ApiDisasterSchema);
  return {
    ...local,
    started_on: live.started_on ?? local.started_on,
    source_url: live.source_url ?? localDisaster().disaster.url,
  };
}

export async function getBoard(slug: string): Promise<BoardData> {
  "use cache";
  const local = localCrisisMeta(slug);
  cacheTag(`crisis:${local.glide_id}`);
  cacheLife("hours");

  if (!LIVE_API_URL) {
    const crisis = await getCrisis(slug);
    const responders = localDataset().orgs.map(toResponder);
    return {
      crisis,
      generated_at: localDisaster().retrieved_at,
      responders,
      government_funds: governmentFunds(),
      facets: buildFacets(responders),
      counts: boardCounts(responders),
    };
  }

  const [crisis, items, freshness] = await Promise.all([
    getCrisis(slug),
    fetchLive(`/v1/disasters/${local.glide_id}/responders?limit=100`, z.array(ApiResponderItemSchema)),
    getFreshness(),
  ]);
  const responders = items.map(apiResponderToLocal);
  return {
    crisis,
    generated_at: freshness.retrieved_at,
    responders,
    government_funds: governmentFunds(),
    facets: buildFacets(responders),
    counts: boardCounts(responders),
  };
}

export async function listOrgIds(): Promise<string[]> {
  "use cache";
  cacheTag(`crisis:${DEFAULT_GLIDE_ID}`);
  cacheLife("hours");

  if (!LIVE_API_URL) {
    return localDataset().orgs.map((o) => o.org_id);
  }
  const items = await fetchLive("/v1/orgs?limit=100", z.array(ApiOrgRefSchema));
  return items.map((o) => o.org_id);
}

export async function getOrg(orgId: string): Promise<OrgDetail> {
  "use cache";
  cacheTag(`org:${orgId}`);
  cacheLife("hours");

  if (!LIVE_API_URL) {
    const raw = localDataset().orgs.find((o) => o.org_id === orgId);
    if (!raw) throw new Error(`Unknown organisation: ${orgId}`);
    return toOrgDetail(raw);
  }
  const live = await fetchLive(`/v1/orgs/${orgId}`, ApiOrgDetailSchema);
  return apiOrgDetailToLocal(live);
}

export async function getFreshness(): Promise<{ retrieved_at: string; source: string }> {
  "use cache";
  cacheTag(`crisis:${DEFAULT_GLIDE_ID}`);
  cacheLife("hours");

  if (!LIVE_API_URL) {
    const disaster = localDisaster();
    return { retrieved_at: disaster.retrieved_at, source: disaster.source };
  }
  const live = await fetchLive("/v1/meta/freshness", ApiFreshnessOutSchema);
  return { retrieved_at: live.generated_at, source: live.jobs?.[0]?.job ?? "spenden-transparenz API" };
}

export async function getSources(): Promise<SourceEntry[]> {
  "use cache";
  cacheTag(`crisis:${DEFAULT_GLIDE_ID}`);
  cacheLife("hours");

  if (!LIVE_API_URL) {
    const disaster = localDisaster();
    return [
      {
        key: "reliefweb",
        name: "ReliefWeb",
        url: "https://reliefweb.int/",
        licence: "ReliefWeb terms of use",
        retrieved_at: disaster.retrieved_at.slice(0, 10),
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
  const live = await fetchLive("/v1/meta/sources", z.array(ApiSourceOutSchema));
  return live.map((s) => ({
    key: s.id,
    name: s.name,
    url: s.url,
    licence: s.licence ?? "unbekannt",
    retrieved_at: s.retrieved_at ?? "",
  }));
}

export async function getCorrections(): Promise<Correction[]> {
  "use cache";
  cacheTag(`crisis:${DEFAULT_GLIDE_ID}`);
  cacheLife("hours");

  // Seeded, not fetched: there is no /v1/corrections endpoint (see apps/api/openapi.json)
  // and there will not be one - this is the site's own editorial record of its mistakes,
  // kept the same whether the live API is configured or not. An empty corrections page
  // would be the least credible page on a transparency site, so it ships pre-filled with
  // the two sampling errors the provenance spot-check in machbarkeit-report.md actually
  // found (section "Provenienz-Stichprobe").
  return [
    {
      date: "2026-08-28",
      org_id: "non-resident-nepali-association",
      org_name: "Non-Resident Nepali Association (NRNA)",
      field: "Präsenz in Nepal seit (Jahr)",
      before:
        "2003, ohne Zitatbeleg (die Stichprobenprüfung fand auf der Startseite an der zitierten Stelle kein Gründungsjahr)",
      after: "2003, belegt durch das Zitat „established October 11, 2003“ auf nrna.org.np",
      source_url: "https://www.nrna.org.np/",
    },
    {
      date: "2026-08-28",
      org_id: "unicef-nepal",
      org_name: "UNICEF Nepal",
      field: "Einnahmen (Konzern, weltweit)",
      before:
        "8.263.000.000 USD, verlinkt auf die Jahresbericht-Seite ohne den Hinweis, dass es eine globale, nicht Nepal-spezifische Zahl ist, und dass sie im Text der Seite nicht direkt auffindbar ist",
      after:
        "8.263.000.000 USD, mit Anmerkung: globale UNICEF-Konzernzahl aus dem Jahresbericht 2024, nicht Nepal-spezifisch, an der zitierten URL nicht maschinell nachprüfbar (die Zahl steht in einem eingebetteten Infogram)",
      source_url: "https://www.unicef.org/reports/unicef-annual-report/2024",
    },
  ];
}
