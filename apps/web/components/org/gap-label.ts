/**
 * Turns a `data_gaps` entry into something a reader can read.
 *
 * The section is called "Was wir nicht wissen". Printing `financial_transparency.income`
 * there answers a reader's question with a database identifier, so every entry is mapped
 * to a sentence instead.
 *
 * The entries are not clean paths. Measured across the 44 pilot records there are 75
 * distinct strings in three shapes:
 *
 *   1. a plain path            "financial_transparency.income"
 *   2. a path plus an English  "names.legal (no register-quality number found)"
 *      qualifier in brackets
 *   3. a whole English sentence with no path at all, for example
 *      "current_response entries lack precise district/municipality-level location detail"
 *
 * Shape 1 and 2 become German sentences, with the qualifier preserved and marked as
 * English rather than dropped, because it is often the most specific thing we know.
 * Shape 3 is passed through untouched and marked as English. Nothing is invented and
 * nothing is silently discarded.
 */

export interface GapLabel {
  /** Message key under `org.gaps.path`, or null when there is no mapping. */
  key: string | null;
  /** Registry code, when the path named one. The caller resolves it to a display name. */
  registry: string | null;
  /** English source text to render after the sentence, marked with lang="en". */
  qualifier: string | null;
  /** Set when the entry is prose rather than a path: render it as English, verbatim. */
  verbatim: string | null;
}

// Registry codes appear inside the brackets of registrations[NP_SWC].identifier.
const REGISTRY_IN_BRACKETS = /^registrations\[([A-Z_]+)\]/;

const PATH_KEYS: Record<string, string> = {
  "names.legal": "names_legal",
  "names.local_script": "names_local_script",
  "names.aliases": "names_aliases",
  "hq.city": "hq_city",
  website: "website",
  "nepal_presence.since_year": "presence_since_year",
  "nepal_presence.mode": "presence_mode",
  "nepal_presence.staff_count": "presence_staff_count",
  "nepal_presence.partners": "presence_partners",
  registrations: "registrations_all",
  "registrations[*]": "registration_entry",
  "registrations[*].identifier": "registration_identifier",
  "registrations[*].url": "registration_url",
  "registrations[*].status": "registration_status",
  financial_transparency: "financial_all",
  "financial_transparency.income": "financial_income",
  "financial_transparency.expenditure": "financial_expenditure",
  "financial_transparency.program_ratio": "financial_program_ratio",
  "financial_transparency.annual_report": "financial_annual_report",
  "financial_transparency.annual_report.url": "financial_annual_report_url",
  "financial_transparency.annual_report.fiscal_year": "financial_fiscal_year",
  "financial_transparency.annual_report.fiscal_year_end": "financial_fiscal_year_end",
  "financial_transparency.audited_financials": "financial_audited",
  "financial_transparency.iati_publisher": "financial_iati",
  "financial_transparency.iati_publisher.is_publisher": "financial_iati",
  current_response: "response_none",
  "current_response[*].date": "response_date",
  "current_response[*].amount": "response_amount",
  "current_response[*].where": "response_where",
  "current_response[*].quote": "response_quote",
  "current_response[*].source_url": "response_source_url",
  warnings: "warnings_none",
};

export function gapLabel(entry: string): GapLabel {
  const trimmed = entry.trim();

  // Split "names.legal (no register-quality number found)" into path and qualifier.
  const bracketed = trimmed.match(/^([^(]+?)\s*\((.+)\)\s*$/);
  const head = (bracketed?.[1] ?? trimmed).trim();
  const qualifier = bracketed?.[2]?.trim() ?? null;

  // A path is dotted or indexed and contains no spaces. Anything else is prose.
  const looksLikePath = /^[a-z_]+(\[[^\]]*\])?(\.[a-z_]+(\[[^\]]*\])?)*$/.test(head);
  if (!looksLikePath) {
    return { key: null, registry: null, qualifier: null, verbatim: trimmed };
  }

  const registry = head.match(REGISTRY_IN_BRACKETS)?.[1];
  const normalised = head.replace(/\[[^\]]*\]/g, "[*]");
  const key = PATH_KEYS[normalised] ?? PATH_KEYS[head] ?? null;

  if (!key) {
    // No mapping. Show the path rather than pretend, but say what it is.
    return { key: "unmapped", registry: null, qualifier: head, verbatim: null };
  }

  return { key, registry: registry ?? null, qualifier, verbatim: null };
}
