import { describe, expect, it } from "vitest";
import type { Datum, GapReason, OrgDetail } from "@/lib/types";

import { groupDataGaps, resolveGapReason } from "./gap-reason";

function gapDatum<T = string>(reason: GapReason, note: string | null = null): Datum<T> {
  return {
    value: null,
    is_gap: true,
    source_url: null,
    publisher: null,
    retrieved_at: "2026-08-28",
    published_at: null,
    verification: "unverified",
    quote: null,
    note,
    gap_reason: reason,
  };
}

function valueDatum<T>(value: T): Datum<T> {
  return {
    value,
    is_gap: false,
    source_url: "https://example.org/a",
    publisher: "example.org",
    retrieved_at: "2026-08-28",
    published_at: null,
    verification: "third_party_reported",
    quote: null,
    note: null,
    gap_reason: null,
  };
}

const org: OrgDetail = {
  org_id: "test-org",
  name: "Test Org",
  local_script: gapDatum("not_searched"),
  legal_name: gapDatum("not_searched"),
  aliases: [],
  org_type: "ingo",
  hq_country: "NP",
  hq_city: null,
  website: null,
  last_updated: "2026-08-28",
  statements: [],
  presence: {
    since_year: valueDatum(1990),
    mode: valueDatum("own_staff"),
    staff_count: gapDatum<number>("searched_not_found"),
    partners: [],
  },
  registrations: [
    {
      registry: "NP_SWC",
      datum: gapDatum("source_unreachable", "swc.org.np was unreachable during this session."),
      register_url: null,
      status: null,
    },
    {
      registry: "IATI",
      datum: valueDatum("ORG-1"),
      register_url: "https://dashboard.iatistandard.org/publishers/org1/",
      status: "active publisher",
    },
  ],
  financials: {
    annual_report: gapDatum("searched_not_found"),
    audited: gapDatum("searched_not_found"),
    iati_ref: valueDatum("ORG-1"),
    income: gapDatum<number>("searched_not_found"),
    expenditure: gapDatum<number>("searched_not_found"),
    program_ratio: gapDatum<number>("not_public"),
    currency: null,
    fiscal_year: null,
    scope: null,
  },
  warnings: [],
  data_gaps: [],
  research_notes: null,
};

describe("resolveGapReason", () => {
  it("resolves a dotted name path to its structured datum", () => {
    expect(resolveGapReason("names.legal", org)).toBe("not_searched");
  });

  it("resolves a registrations[REGISTRY].identifier path to that registration's datum", () => {
    expect(resolveGapReason("registrations[NP_SWC].identifier", org)).toBe("source_unreachable");
  });

  it("resolves a financial_transparency path to its structured datum", () => {
    expect(resolveGapReason("financial_transparency.program_ratio", org)).toBe("not_public");
  });

  it("resolves nepal_presence.staff_count to its structured datum", () => {
    expect(resolveGapReason("nepal_presence.staff_count", org)).toBe("searched_not_found");
  });

  it("does not resolve a registrations[...] path for a registry that is not a gap", () => {
    // IATI has a value in this fixture; a stray gap-path for it still needs a reason, so
    // it falls through to the text heuristic rather than reading a value's null fields.
    expect(resolveGapReason("registrations[IATI].identifier", org)).toBe("searched_not_found");
  });

  it("falls back to a text heuristic for free-text notes mentioning unreachability", () => {
    expect(
      resolveGapReason("registrations (a register was unreachable during this session)", org),
    ).toBe("source_unreachable");
  });

  it("falls back to a text heuristic for free-text notes mentioning non-publication", () => {
    expect(resolveGapReason("this figure is not published by the register", org)).toBe(
      "not_public",
    );
  });

  it("defaults unresolved free text to searched_not_found, the measured majority case", () => {
    expect(
      resolveGapReason(
        "current_response entries lack precise district-level location detail",
        org,
      ),
    ).toBe("searched_not_found");
  });
});

describe("groupDataGaps", () => {
  it("groups paths under their resolved reason and keeps every reason key present", () => {
    const groups = groupDataGaps(
      ["names.legal", "registrations[NP_SWC].identifier", "financial_transparency.program_ratio"],
      org,
    );
    expect(groups.not_searched).toEqual(["names.legal"]);
    expect(groups.source_unreachable).toEqual(["registrations[NP_SWC].identifier"]);
    expect(groups.not_public).toEqual(["financial_transparency.program_ratio"]);
    expect(groups.searched_not_found).toEqual([]);
  });

  it("returns empty arrays for every reason when there are no gaps", () => {
    const groups = groupDataGaps([], org);
    expect(groups).toEqual({
      searched_not_found: [],
      not_searched: [],
      source_unreachable: [],
      not_public: [],
    });
  });
});
