// The shared vocabulary of the whole frontend. Regenerated from apps/api/openapi.json
// once the backend ships it; until then this file is the contract and is checked
// against schema/org.schema.json by hand.

export type Verification =
  | "register_confirmed"
  | "externally_audited"
  | "self_reported"
  | "third_party_reported"
  | "unverified";

export type GapReason =
  | "not_searched"
  | "searched_not_found"
  | "source_unreachable"
  | "not_public";

export type DatumState =
  | "value"
  | "value_unverified"
  | "not_found"
  | "source_unreachable"
  | "not_public"
  | "stale";

/**
 * Every provenance-carrying value in the product. The key is never absent and the
 * object is never undefined: a missing fact is `value: null` with `is_gap: true` and a
 * reason, because "we looked and did not find it" is information, not emptiness.
 */
export interface Datum<T = unknown> {
  value: T | null;
  is_gap: boolean;
  source_url: string | null;
  publisher: string | null;
  retrieved_at: string | null;
  published_at: string | null;
  verification: Verification;
  quote: string | null;
  note: string | null;
  gap_reason: GapReason | null;
}

export type DonationChannelType = "donation_page" | "platform_page" | "bank_transfer_page";

/**
 * Where an organisation says it takes donations, on its own domain, with the provenance
 * of that claim. This is an information field like every other: it is never a
 * recommendation, it carries no ranking, and an organisation without one is not worse
 * than an organisation with one. `url` is null for the ten organisations where a real
 * search found no official channel, and that state renders at full weight.
 *
 * Account numbers are deliberately absent from this type. The product links to the
 * organisation's own page and never transcribes bank details, so there is no field here
 * that could hold them.
 */
export interface DonationChannel {
  url: string | null;
  channel_type: DonationChannelType | null;
  /** True when the page is specific to this flood, false when it is the general one. */
  flood_specific: boolean | null;
  source_url: string | null;
  /** Host shown to the reader, e.g. "donation.nrcs.org". */
  publisher: string | null;
  retrieved_at: string | null;
  verification: Verification;
  quote: string | null;
  note: string | null;
  gap_reason: GapReason | null;
}

/**
 * What a board row needs to render the link and its provenance chip. The research
 * note behind a channel runs to several sentences and there are 44 of them, which is
 * 12 KB of prose nobody reads on the board; it stays on the organisation page, where
 * it is actually shown. Sending the whole record to the board cost 25 KB of payload
 * and breached the budget test in lib/api.test.ts.
 */
export type DonationLink = Pick<
  DonationChannel,
  "url" | "retrieved_at" | "verification" | "gap_reason"
>;

/** A state relief fund. Same shape, but it is not an organisation on the board. */
export interface GovernmentFund extends DonationChannel {
  name: string;
}

export type OrgType =
  | "un_agency"
  | "red_cross_movement"
  | "ingo"
  | "national_ngo"
  | "community_org"
  | "diaspora_charity"
  | "foundation"
  | "government"
  | "platform"
  | "alliance"
  | "unknown";

/**
 * An amount is never rendered without saying what kind of amount it is. The order here
 * is roughly weakest claim to strongest; when the source text is ambiguous the weaker
 * label wins, because overstating a pledge as a payment is the exact harm this product
 * exists to prevent. In the pilot data nothing is "disbursed", which is the finding.
 */
export type AmountBasis =
  | "reported"
  | "appeal"
  | "pledged"
  | "raised"
  | "released"
  | "disbursed";

export interface DistrictRef {
  code: string;
  name: string;
}

export interface Statement {
  id: string;
  /** Empty means no location was stated. It never means "nowhere". */
  districts: DistrictRef[];
  happened_on: string | null;
  amount: number | null;
  currency: string | null;
  amount_basis: AmountBasis | null;
  /** datum.value is the activity sentence, so the sentence cannot exist without its source. */
  datum: Datum<string>;
}

export interface Responder {
  org_id: string | null;
  org_name_raw: string;
  name: string;
  local_script: string | null;
  aliases: string[];
  org_type: OrgType;
  hq_country: string;
  is_local: boolean;
  /** Lowercased, diacritics folded, name plus aliases. Built once, never per keystroke. */
  search_key: string;
  statements: Statement[];
  donation: DonationLink;
}

export interface Crisis {
  glide_id: string;
  slug: string;
  name_de: string;
  name_en: string;
  started_on: string;
  source_url: string;
}

export interface Facet {
  key: string;
  label_key: string;
  count: number;
}

export interface BoardData {
  crisis: Crisis;
  generated_at: string;
  responders: Responder[];
  /** Not organisations and never counted as such. Rendered apart from the list. */
  government_funds: GovernmentFund[];
  facets: {
    districts: Facet[];
    hq: Facet[];
    orgType: Facet[];
    verification: Facet[];
  };
  counts: {
    orgs: number;
    statements: number;
    districts: number;
    orgsWithoutResponse: number;
  };
}

export interface Registration {
  registry: string;
  /** value is the identifier. A null identifier keeps its row; that row is the honest one. */
  datum: Datum<string>;
  register_url: string | null;
  status: string | null;
}

export interface OrgDetail {
  org_id: string;
  name: string;
  local_script: Datum<string>;
  legal_name: Datum<string>;
  aliases: string[];
  org_type: OrgType;
  hq_country: string;
  hq_city: string | null;
  website: string | null;
  last_updated: string;
  donation: DonationChannel;
  statements: Statement[];
  presence: {
    since_year: Datum<number>;
    mode: Datum<string>;
    staff_count: Datum<number>;
    partners: Datum<string>[];
  };
  registrations: Registration[];
  financials: {
    annual_report: Datum<string>;
    audited: Datum<string>;
    iati_ref: Datum<string>;
    income: Datum<number>;
    expenditure: Datum<number>;
    program_ratio: Datum<number>;
    currency: string | null;
    fiscal_year: string | null;
    scope: string | null;
  };
  warnings: { type: string; datum: Datum<string> }[];
  data_gaps: string[];
  research_notes: string | null;
}

export interface SourceEntry {
  key: string;
  name: string;
  url: string;
  licence: string;
  retrieved_at: string;
}

export interface Correction {
  date: string;
  org_id: string;
  org_name: string;
  field: string;
  before: string;
  after: string;
  source_url: string;
}
