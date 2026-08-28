import { brotliCompressSync, constants, gzipSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { getBoard, getCrisis, getFreshness, getOrg, listOrgIds } from "./api";

const board = await getBoard("nepal-flut-2026");

describe("board data", () => {
  it("has the measured shape of the pilot dataset", () => {
    expect(board.responders).toHaveLength(44);
    expect(board.counts.orgs).toBe(44);
    expect(board.counts.statements).toBe(44);
    expect(board.counts.orgsWithoutResponse).toBe(9);
    expect(board.responders.filter((r) => r.is_local)).toHaveLength(14);
  });

  it("counts six named districts, not the three the spec assumed", () => {
    expect(board.counts.districts).toBe(6);
    expect(board.facets.districts.map((f) => f.key)).toContain("NP0329");
  });

  it("offers a facet for statements with no stated location", () => {
    const none = board.facets.districts.find((f) => f.key === "none");
    expect(none).toBeDefined();
    expect(none!.count).toBeGreaterThan(0);
  });

  it("keeps every facet value even when nothing matches it, so the filter never looks broken", () => {
    const keys = board.facets.verification.map((f) => f.key);
    expect(keys).toEqual([
      "register_confirmed",
      "externally_audited",
      "self_reported",
      "third_party_reported",
      "unverified",
    ]);
    expect(board.facets.verification.find((f) => f.key === "register_confirmed")!.count).toBe(0);
    // Facet counts are organisation counts, not statement counts, because the list being
    // filtered is a list of organisations and a count should predict the result size.
    // 27 statements are self-reported; they belong to 24 organisations.
    expect(board.facets.verification.find((f) => f.key === "self_reported")!.count).toBe(24);
    expect(board.facets.verification.find((f) => f.key === "third_party_reported")!.count).toBe(13);
  });

  it("stays inside the payload budget with notes kept", () => {
    const raw = Buffer.from(JSON.stringify(board), "utf8");
    const brotli = brotliCompressSync(raw, {
      params: { [constants.BROTLI_PARAM_QUALITY]: 11 },
    }).byteLength;
    const gzip = gzipSync(raw, { level: 9 }).byteLength;
    // Printed on every run so a regression is visible before it breaches.
    console.log(`board payload: raw ${raw.byteLength} B, brotli ${brotli} B, gzip ${gzip} B`);
    // The spec's budget is stated in brotli, which is what a browser actually receives.
    expect(raw.byteLength).toBeLessThanOrEqual(60_000);
    expect(brotli).toBeLessThanOrEqual(12_000);
  });

  it("turns an unstated location into an empty district list, never a fake district", () => {
    const all = board.responders.flatMap((r) => r.statements);
    expect(all.some((s) => s.districts.length === 0)).toBe(true);
    expect(all.every((s) => s.districts.every((d) => /^NP\d{4}$/.test(d.code)))).toBe(true);
  });

  it("gives every statement a source, because the sentence and its source are one object", () => {
    const all = board.responders.flatMap((r) => r.statements);
    expect(all.every((s) => typeof s.datum.value === "string" && s.datum.value.length > 0)).toBe(true);
    expect(all.every((s) => s.datum.source_url !== null)).toBe(true);
  });

  it("never carries a quote longer than 40 words", () => {
    const quotes = board.responders
      .flatMap((r) => r.statements)
      .map((s) => s.datum.quote)
      .filter((q): q is string => q !== null);
    expect(quotes.length).toBeGreaterThan(0);
    expect(quotes.every((q) => q.split(/\s+/).length <= 40)).toBe(true);
  });

  it("labels every amount with a basis, so no bare figure can reach the page", () => {
    const withAmount = board.responders
      .flatMap((r) => r.statements)
      .filter((s) => s.amount !== null);
    expect(withAmount).toHaveLength(9);
    expect(withAmount.every((s) => s.amount_basis !== null && s.currency !== null)).toBe(true);
  });

  it("precomputes a folded search key rather than normalising per keystroke", () => {
    const msf = board.responders.find((r) => r.org_id === "msf-international");
    expect(msf!.search_key).toContain("medecins");
    expect(msf!.search_key).toBe(msf!.search_key.toLowerCase());
  });
});

describe("crisis", () => {
  it("carries the GLIDE id", async () => {
    const c = await getCrisis("nepal-flut-2026");
    expect(c.glide_id).toBe("ff-2026-000162-npl");
  });
});

describe("organisations", () => {
  it("lists 44 ids", async () => expect(await listOrgIds()).toHaveLength(44));

  it("keeps registration rows whose identifier was never found", async () => {
    const nrcs = await getOrg("nepal-red-cross-society");
    const swc = nrcs.registrations.find((r) => r.registry === "NP_SWC");
    expect(swc).toBeDefined();
    expect(swc!.datum.value).toBeNull();
    expect(swc!.datum.is_gap).toBe(true);
  });

  it("reads an unreachable register as source_unreachable, not as absence", async () => {
    const nrcs = await getOrg("nepal-red-cross-society");
    const swc = nrcs.registrations.find((r) => r.registry === "NP_SWC")!;
    expect(swc.datum.gap_reason).toBe("source_unreachable");
  });

  it("marks a gap with no note as not_searched rather than claiming a search happened", async () => {
    const club = await getOrg("the-rising-youth-club");
    expect(club.legal_name.value).toBeNull();
    expect(club.legal_name.note).toBeNull();
    expect(club.legal_name.gap_reason).toBe("not_searched");
  });

  it("marks a gap with a note as searched_not_found", async () => {
    const nrcs = await getOrg("nepal-red-cross-society");
    expect(nrcs.financials.income.value).toBeNull();
    expect(nrcs.financials.income.gap_reason).toBe("searched_not_found");
  });

  it("carries the Devanagari name where one exists", async () => {
    const club = await getOrg("the-rising-youth-club");
    expect(club.local_script.value).toBe("द राइजिङ युवा क्लब");
  });

  it("reports no Nepali organisation with a public income figure", async () => {
    const ids = await listOrgIds();
    const orgs = await Promise.all(ids.map((id) => getOrg(id)));
    const nepali = orgs.filter((o) => o.hq_country === "NP");
    expect(nepali).toHaveLength(14);
    expect(nepali.filter((o) => o.financials.income.value !== null)).toHaveLength(0);
  });

  it("has no warnings anywhere in the pilot data", async () => {
    const ids = await listOrgIds();
    const orgs = await Promise.all(ids.map((id) => getOrg(id)));
    expect(orgs.flatMap((o) => o.warnings)).toHaveLength(0);
  });
});

describe("freshness", () => {
  it("reports when the data was retrieved", async () => {
    const f = await getFreshness();
    expect(f.retrieved_at).toMatch(/^\d{4}-\d{2}-\d{2}/);
  });
});
