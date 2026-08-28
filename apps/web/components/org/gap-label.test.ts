import { describe, expect, it } from "vitest";
import { gapLabel } from "./gap-label";

describe("gapLabel", () => {
  it("maps a plain path to a message key", () => {
    expect(gapLabel("financial_transparency.income")).toEqual({
      key: "financial_income",
      registry: null,
      qualifier: null,
      verbatim: null,
    });
  });

  it("pulls the registry code out of an indexed path", () => {
    const label = gapLabel("registrations[NP_SWC].identifier");
    expect(label.key).toBe("registration_identifier");
    expect(label.registry).toBe("NP_SWC");
  });

  it("keeps the English qualifier instead of dropping it", () => {
    const label = gapLabel("names.legal (no register-quality number found)");
    expect(label.key).toBe("names_legal");
    expect(label.qualifier).toBe("no register-quality number found");
  });

  it("passes prose through verbatim rather than mangling it into a path", () => {
    const entry = "current_response entries lack precise district/municipality-level location detail";
    expect(gapLabel(entry)).toEqual({ key: null, registry: null, qualifier: null, verbatim: entry });
  });

  it("treats a parenthesised note with no path as prose", () => {
    const entry = "financial_transparency (entire section - no DZI, ITZ, or annual report found)";
    const label = gapLabel(entry);
    expect(label.key).toBe("financial_all");
    expect(label.qualifier).toBe("entire section - no DZI, ITZ, or annual report found");
  });

  it("never returns a bare path as the displayed text", () => {
    const label = gapLabel("some.unknown.path");
    expect(label.key).toBe("unmapped");
    expect(label.qualifier).toBe("some.unknown.path");
  });

  it("covers every data_gaps entry in the pilot dataset", async () => {
    const { listOrgIds, getOrg } = await import("@/lib/api");
    const ids = await listOrgIds();
    const orgs = await Promise.all(ids.map((id) => getOrg(id)));
    const entries = orgs.flatMap((o) => o.data_gaps);
    expect(entries.length).toBeGreaterThan(400);
    // Every entry resolves to a sentence, verbatim prose, or an explicit "unmapped"
    // marker. None may fall through to a raw path rendered as if it were German.
    for (const entry of entries) {
      const label = gapLabel(entry);
      expect(label.key !== null || label.verbatim !== null).toBe(true);
    }
    // And the great majority get a real sentence, not the unmapped fallback.
    const unmapped = entries.filter((e) => gapLabel(e).key === "unmapped");
    expect(unmapped.length / entries.length).toBeLessThan(0.02);
  });
});
