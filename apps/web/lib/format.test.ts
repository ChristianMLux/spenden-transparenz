import { describe, expect, it } from "vitest";
import { domainOf, formatDate, relativeDays } from "./format";

const NOW = new Date("2026-08-28T12:00:00Z");

describe("formatDate", () => {
  it("writes a German date as day.month.year", () => {
    expect(formatDate("2026-08-27", "de")).toBe("27.08.2026");
  });
  it("writes an English date with a spelled month, so 08/07 is never ambiguous", () => {
    expect(formatDate("2026-08-27", "en")).toBe("27 Aug 2026");
  });
  it("does not shift the day across a timezone", () => {
    expect(formatDate("2026-01-01", "de")).toBe("01.01.2026");
  });
});

describe("relativeDays", () => {
  it("counts today as zero", () => expect(relativeDays("2026-08-28", NOW)).toBe(0));
  it("counts yesterday as one", () => expect(relativeDays("2026-08-27", NOW)).toBe(1));
  it("counts a two-month-old reading in days", () => {
    expect(relativeDays("2026-06-01", NOW)).toBe(88);
  });
  it("returns a negative number for a future date rather than throwing", () => {
    expect(relativeDays("2026-08-30", NOW)).toBe(-2);
  });
});

describe("domainOf", () => {
  it("shows the host without www, because that is what the reader recognises", () => {
    expect(domainOf("https://www.reliefweb.int/report/nepal/x")).toBe("reliefweb.int");
  });
  it("keeps a meaningful subdomain", () => {
    expect(domainOf("https://projects.propublica.org/nonprofits/organizations/1")).toBe(
      "projects.propublica.org",
    );
  });
  it("returns null for a missing url instead of an empty string", () => {
    expect(domainOf(null)).toBeNull();
  });
  it("returns null for a malformed url instead of throwing", () => {
    expect(domainOf("not a url")).toBeNull();
  });
});
