import { describe, expect, it } from "vitest";
import { getBoard } from "./api";
import { applyFilters, EMPTY, parseFilters, serializeFilters } from "./filter";
import type { FilterState } from "./filter";
import type { Responder } from "./types";

const board = await getBoard("nepal-flut-2026");
const all = board.responders;

describe("applyFilters", () => {
  it("returns everything when nothing is selected", () => {
    expect(applyFilters(all, EMPTY)).toHaveLength(44);
  });

  it("ORs within a group", () => {
    const only = applyFilters(all, { ...EMPTY, districts: ["NP0329", "NP0328"] });
    expect(only.length).toBeGreaterThan(
      applyFilters(all, { ...EMPTY, districts: ["NP0329"] }).length - 1,
    );
    expect(
      only.every((r) =>
        r.statements.some((s) => s.districts.some((d) => d.code === "NP0329" || d.code === "NP0328")),
      ),
    ).toBe(true);
  });

  it("ANDs between groups", () => {
    const r = applyFilters(all, { ...EMPTY, districts: ["NP0329"], hq: ["local"] });
    expect(r.every((x) => x.is_local)).toBe(true);
  });

  it('treats "none" as statements with no stated location', () => {
    const r = applyFilters(all, { ...EMPTY, districts: ["none"] });
    expect(r.length).toBeGreaterThan(0);
    expect(r.every((x) => x.statements.some((s) => s.districts.length === 0))).toBe(true);
  });

  it("keeps orgs with no response when no statement filter is active", () => {
    expect(applyFilters(all, { ...EMPTY, hq: ["local"] }).some((r) => r.statements.length === 0)).toBe(
      true,
    );
  });

  it("EMPTY never hides an organisation for lacking a response (has_response defaults to null)", () => {
    expect(EMPTY.has_response).toBeNull();
    expect(applyFilters(all, EMPTY).some((r) => r.statements.length === 0)).toBe(true);
  });

  it("has_response=false shows only organisations with no statement, not a reordering", () => {
    const r = applyFilters(all, { ...EMPTY, has_response: false });
    expect(r.length).toBe(9);
    expect(r.every((x) => x.statements.length === 0)).toBe(true);
  });

  it("has_response=true shows only organisations with at least one statement", () => {
    const r = applyFilters(all, { ...EMPTY, has_response: true });
    expect(r.length).toBe(35);
    expect(r.every((x) => x.statements.length > 0)).toBe(true);
  });

  it("has_response combines with other filters (AND)", () => {
    const r = applyFilters(all, { ...EMPTY, has_response: false, hq: ["local"] });
    expect(r.every((x) => x.statements.length === 0 && x.is_local)).toBe(true);
  });

  it("searches name and aliases, diacritics folded", () => {
    expect(applyFilters(all, { ...EMPTY, q: "nrcs" }).map((r) => r.org_id)).toContain(
      "nepal-red-cross-society",
    );
    expect(applyFilters(all, { ...EMPTY, q: "medecins" }).length).toBe(1);
  });

  it("offers no sort by evidence grade", () => {
    // The type has three values. If a fourth appears, this test is the tripwire.
    const sorts: FilterState["sort"][] = ["latest", "name", "fewest-data"];
    expect(sorts).toHaveLength(3);
  });

  it("round-trips through search params", () => {
    const f: FilterState = { ...EMPTY, districts: ["NP0329"], hq: ["local"], q: "red cross" };
    expect(parseFilters(serializeFilters(f))).toEqual(f);
  });

  it("round-trips has_response through search params, true and false distinctly from absent", () => {
    expect(parseFilters(serializeFilters({ ...EMPTY, has_response: false })).has_response).toBe(false);
    expect(parseFilters(serializeFilters({ ...EMPTY, has_response: true })).has_response).toBe(true);
    expect(parseFilters(serializeFilters(EMPTY)).has_response).toBeNull();
  });

  it("sorts latest first by default, most recent statement wins", () => {
    const sorted = applyFilters(all, { ...EMPTY, sort: "latest" });
    // Every org appears exactly once, orgs without statements are not silently dropped
    expect(sorted).toHaveLength(44);
  });

  it("sorts A to Z by name", () => {
    const sorted = applyFilters(all, { ...EMPTY, sort: "name" });
    const names = sorted.map((r) => r.name.toLowerCase());
    const expected = [...names].sort((a, b) => a.localeCompare(b));
    expect(names).toEqual(expected);
  });

  it("sorts fewest-data first: orgs with no statements come before orgs with statements", () => {
    const sorted = applyFilters(all, { ...EMPTY, sort: "fewest-data" });
    const firstWithStatement = sorted.findIndex((r) => r.statements.length > 0);
    const lastWithoutStatement = sorted.map((r) => r.statements.length === 0).lastIndexOf(true);
    expect(lastWithoutStatement).toBeLessThan(firstWithStatement);
  });

  it("performs well: 4400 synthetic rows filter in under 16ms", () => {
    const synthetic: Responder[] = [];
    for (let i = 0; i < 100; i++) {
      for (const r of all) {
        synthetic.push({ ...r, org_id: `${r.org_id ?? r.org_name_raw}-${i}` });
      }
    }
    expect(synthetic).toHaveLength(4400);
    const start = performance.now();
    applyFilters(synthetic, { ...EMPTY, districts: ["NP0329"], hq: ["local"], q: "red" });
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(16);
  });
});
