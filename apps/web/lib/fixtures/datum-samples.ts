import type { Datum } from "@/lib/types";

const base: Datum<string> = {
  value: "Kathmandu",
  is_gap: false,
  source_url: "https://reliefweb.int/report/nepal/nepal-flood-response-situation-report-1",
  publisher: "reliefweb.int",
  retrieved_at: "2026-08-28",
  published_at: "2026-08-27",
  verification: "third_party_reported",
  quote: null,
  note: null,
  gap_reason: null,
};

const gap: Datum<string> = {
  ...base,
  value: null,
  is_gap: true,
  source_url: null,
  publisher: null,
  quote: null,
  verification: "unverified",
  gap_reason: "searched_not_found",
};

export interface Sample {
  key: string;
  field: string;
  fieldEn: string;
  datum: Datum<string>;
  staleAfterDays?: number;
  /** Marked when the sample exists to show a label variant rather than a sixth state. */
  variantOf?: string;
}

/**
 * The six states, plus the three cases that break renderers in practice: the label
 * variant of not_found, a gap whose note is genuinely absent (this exists in the real
 * data), and a value carrying a long quote.
 */
export const SAMPLES: Sample[] = [
  {
    key: "value",
    field: "Einnahmen",
    fieldEn: "Income",
    datum: {
      ...base,
      value: "GBP 1.842.000",
      verification: "register_confirmed",
      quote: "Total income for the financial year ending 31 March 2025 was 1,842,000 pounds.",
      note: "Geschäftsjahr endet am 31.03.2025, Umfang: weltweit.",
      source_url: "https://register-of-charities.charitycommission.gov.uk/en/charity-search",
      publisher: "register-of-charities.charitycommission.gov.uk",
    },
  },
  {
    key: "value_unverified",
    field: "Beschäftigte in Nepal",
    fieldEn: "Staff in Nepal",
    datum: {
      ...base,
      value: "rund 120",
      verification: "unverified",
      note: "Die Zahl steht in einer Pressemeldung, nicht in einem Bericht der Organisation.",
    },
  },
  {
    key: "not_found",
    field: "Einnahmen",
    fieldEn: "Income",
    datum: {
      ...gap,
      note: "Auf der Website, im Jahresberichtsbereich und im Sozialregister gesucht.",
      gap_reason: "searched_not_found",
    },
  },
  {
    key: "source_unreachable",
    field: "Registriernummer (Social Welfare Council)",
    fieldEn: "Registration number (Social Welfare Council)",
    datum: {
      ...gap,
      note: "swc.org.np war am 28.08.2026 nicht erreichbar.",
      gap_reason: "source_unreachable",
    },
  },
  {
    key: "not_public",
    field: "Programmquote",
    fieldEn: "Programme ratio",
    datum: {
      ...gap,
      note: "Unter 500.000 Pfund Einnahmen verlangt das Register keine Aufschlüsselung.",
      gap_reason: "not_public",
    },
  },
  {
    key: "stale",
    field: "Präsenz in Nepal seit",
    fieldEn: "Present in Nepal since",
    datum: {
      ...base,
      value: "2015",
      verification: "self_reported",
      retrieved_at: "2026-05-02",
      note: "Angabe von der Startseite der Organisation.",
    },
  },
  {
    key: "not_searched",
    field: "Eingetragener Name",
    fieldEn: "Legal name",
    variantOf: "not_found",
    datum: { ...gap, note: null, gap_reason: "not_searched" },
  },
  {
    key: "gap_without_note",
    field: "Beschäftigte in Nepal",
    fieldEn: "Staff in Nepal",
    variantOf: "not_found",
    datum: { ...gap, note: null, gap_reason: "searched_not_found" },
  },
  {
    key: "long_quote",
    field: "Reaktion",
    fieldEn: "Response",
    variantOf: "value",
    datum: {
      ...base,
      value:
        "World Vision Nepal bereitet eine 90-tägige humanitäre Reaktion mit Nothilfe, Unterkünften, Hygiene und Schutz für gefährdete Familien vor.",
      verification: "self_reported",
      quote:
        "preparing a 90-day humanitarian response focused on emergency food assistance, shelter support, hygiene and protection services for vulnerable families.",
      note: "Der Bericht nennt keine Distrikte, die Distriktangabe stammt aus der Meldung selbst.",
    },
  },
];
