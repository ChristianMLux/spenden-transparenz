import { describe, expect, it } from "vitest";
import type { Datum } from "@/lib/types";
import { datumState, gapLabelKey } from "./state";

const NOW = new Date("2026-08-28T12:00:00Z");

const value: Datum<string> = {
  value: "Kathmandu",
  is_gap: false,
  source_url: "https://reliefweb.int/report/nepal/x",
  publisher: "reliefweb.int",
  retrieved_at: "2026-08-28",
  published_at: "2026-08-27",
  verification: "third_party_reported",
  quote: null,
  note: null,
  gap_reason: null,
};

const gap: Datum<string> = {
  ...value,
  value: null,
  is_gap: true,
  source_url: null,
  publisher: null,
  verification: "unverified",
  gap_reason: "searched_not_found",
};

describe("datumState with a value", () => {
  it("a fresh confirmed value is just a value", () => {
    expect(datumState({ ...value, verification: "register_confirmed" }, { now: NOW })).toBe("value");
  });

  it("an unverified value gets its own state so it cannot pass as confirmed", () => {
    expect(datumState({ ...value, verification: "unverified" }, { now: NOW })).toBe("value_unverified");
  });

  it("a value read long ago is stale", () => {
    expect(datumState({ ...value, retrieved_at: "2026-06-01" }, { now: NOW })).toBe("stale");
  });

  it("unverified beats stale, because the weaker claim is the one worth showing", () => {
    expect(
      datumState({ ...value, retrieved_at: "2026-06-01", verification: "unverified" }, { now: NOW }),
    ).toBe("value_unverified");
  });

  it("respects a custom staleness threshold", () => {
    expect(datumState({ ...value, retrieved_at: "2026-08-20" }, { now: NOW })).toBe("value");
    expect(datumState({ ...value, retrieved_at: "2026-08-20" }, { now: NOW, staleAfterDays: 3 })).toBe(
      "stale",
    );
  });

  it("is not stale exactly on the threshold, only past it", () => {
    expect(datumState({ ...value, retrieved_at: "2026-07-29" }, { now: NOW })).toBe("value");
    expect(datumState({ ...value, retrieved_at: "2026-07-28" }, { now: NOW })).toBe("stale");
  });

  it("a value with no retrieval date is not stale, because we do not know that it is", () => {
    expect(datumState({ ...value, retrieved_at: null }, { now: NOW })).toBe("value");
  });

  it("a future retrieval date is never stale", () => {
    expect(datumState({ ...value, retrieved_at: "2026-09-30" }, { now: NOW })).toBe("value");
  });
});

describe("datumState with a gap", () => {
  it("searched and not found is not_found", () => {
    expect(datumState({ ...gap, gap_reason: "searched_not_found" }, { now: NOW })).toBe("not_found");
  });

  it("not searched shares the not_found appearance", () => {
    expect(datumState({ ...gap, gap_reason: "not_searched" }, { now: NOW })).toBe("not_found");
  });

  it("an unreachable source is its own state, not an absence", () => {
    expect(datumState({ ...gap, gap_reason: "source_unreachable" }, { now: NOW })).toBe(
      "source_unreachable",
    );
  });

  it("a register that does not publish the value is its own state", () => {
    expect(datumState({ ...gap, gap_reason: "not_public" }, { now: NOW })).toBe("not_public");
  });

  it("a gap with no reason still renders as not_found, never as blank", () => {
    expect(datumState({ ...gap, gap_reason: null }, { now: NOW })).toBe("not_found");
  });

  it("a gap is never stale, because there is no reading to age", () => {
    expect(
      datumState({ ...gap, retrieved_at: "2020-01-01", gap_reason: "searched_not_found" }, { now: NOW }),
    ).toBe("not_found");
  });

  it("ignores is_gap and trusts value, so one inconsistent record cannot blank a page", () => {
    expect(datumState({ ...value, is_gap: true }, { now: NOW })).toBe("value");
  });
});

describe("gapLabelKey", () => {
  it("distinguishes not searched from searched and not found", () => {
    expect(gapLabelKey({ ...gap, gap_reason: "not_searched" })).toBe("not_searched");
    expect(gapLabelKey({ ...gap, gap_reason: "searched_not_found" })).toBe("not_found");
    expect(gapLabelKey({ ...gap, gap_reason: null })).toBe("not_found");
  });
});
