import { brotliCompressSync, constants, gzipSync } from "node:zlib";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// "use cache" functions call cacheTag()/cacheLife() from next/cache. Outside a real
// Next.js build or server - which is exactly what this Vitest run is - there is no
// "use cache" work-unit store for them to attach to, and the real implementations throw
// ("cacheTag() can only be called inside a 'use cache' function"). Mocking the module is
// the standard way to unit-test a "use cache" function directly: it proves the loader's
// own logic without pulling in Next's server runtime, which no unit test in this repo
// starts. revalidateTag is mocked too, for symmetry, even though this file never calls it.
vi.mock("next/cache", () => ({
  cacheTag: vi.fn(),
  cacheLife: vi.fn(),
  revalidateTag: vi.fn(),
  updateTag: vi.fn(),
  revalidatePath: vi.fn(),
}));

const { RawDatasetSchema, getBoard, getCorrections, getCrisis, getFreshness, getOrg, getSources, listOrgIds } =
  await import("./api");

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
    //
    // Raised for WP4's action path, with the measurement rather than by feel: before the
    // donation link the board was 56,921 B raw / 11,500 B brotli, after it 64,540 /
    // 12,422. The 7.6 KB is what 44 rows of "official channel, its host, the date it was
    // retrieved and the verification word" costs, after the research note and the quote
    // were kept off the board (they stay on the organisation page, where they are shown)
    // and the host was made derivable from the url instead of sent 44 times. It is the
    // floor for the feature, not slack. The product owner confirms this number.
    expect(raw.byteLength).toBeLessThanOrEqual(66_000);
    expect(brotli).toBeLessThanOrEqual(12_800);
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

  // Schema v0.2: gap_reason is read straight from the source record. The org used here
  // (the-rising-youth-club) covered the "no note at all" case under the old note-derived
  // guess; that org's legal_name now carries a research note in the real data (schema
  // v0.2 populates one even for a not_searched field), so the guess and the real field
  // would have agreed there by accident. unicef-nepal's local_script is the real
  // not_searched case the old regex-based guess got wrong: its note reads "Not searched
  // in this research pass." - non-empty text that the old derivation's empty-note check
  // never matched, so it fell through to searched_not_found. Reading the real field
  // fixes exactly that.
  it("marks a gap as not_searched from the real field, not a guess from note text", async () => {
    const unicef = await getOrg("unicef-nepal");
    expect(unicef.local_script.value).toBeNull();
    expect(unicef.local_script.gap_reason).toBe("not_searched");
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

describe("sources and corrections", () => {
  it("lists at least the two sources the board's board.json depends on", async () => {
    const sources = await getSources();
    expect(sources.map((s) => s.key)).toEqual(expect.arrayContaining(["reliefweb", "hapi"]));
    expect(sources.every((s) => s.url.startsWith("https://"))).toBe(true);
  });

  it("seeds the two real sampling errors on day one, never an empty list", async () => {
    const corrections = await getCorrections();
    expect(corrections.length).toBeGreaterThanOrEqual(2);
    const fields = corrections.map((c) => c.org_id);
    expect(fields).toContain("non-resident-nepali-association");
    expect(fields).toContain("unicef-nepal");
    // date, organisation, field, before, after, source - every column populated.
    for (const c of corrections) {
      expect(c.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(c.org_name.length).toBeGreaterThan(0);
      expect(c.field.length).toBeGreaterThan(0);
      expect(c.before.length).toBeGreaterThan(0);
      expect(c.after.length).toBeGreaterThan(0);
      expect(c.source_url.startsWith("https://")).toBe(true);
    }
  });
});

describe("schema validation", () => {
  it("fails on a record missing the required org_id, instead of rendering it as undefined", () => {
    const malformed = {
      generated_at: "2026-08-28T00:00:00Z",
      orgs: [{ names: { common: "No Id Org" }, org_type: "ingo", hq: { country: "NP" }, registrations: [] }],
    };
    const result = RawDatasetSchema.safeParse(malformed);
    expect(result.success).toBe(false);
  });

  it("fails on a gap with no gap_reason, instead of silently treating it as searched_not_found", () => {
    const malformed = {
      generated_at: "2026-08-28T00:00:00Z",
      orgs: [
        {
          org_id: "no-gap-reason-org",
          names: {
            common: "No Gap Reason Org",
            legal: { value: null, source_url: null, note: "not searched" },
          },
          org_type: "ingo",
          hq: { country: "NP" },
          registrations: [],
          nepal_presence: {},
          financial_transparency: {},
          last_updated: "2026-08-28",
        },
      ],
    };
    const result = RawDatasetSchema.safeParse(malformed);
    expect(result.success).toBe(false);
  });

  it("accepts a minimal, well-formed record", () => {
    const minimal = {
      generated_at: "2026-08-28T00:00:00Z",
      orgs: [
        {
          org_id: "minimal-org",
          names: { common: "Minimal Org" },
          org_type: "ingo",
          hq: { country: "NP" },
          registrations: [],
          nepal_presence: {},
          financial_transparency: {},
          last_updated: "2026-08-28",
        },
      ],
    };
    const result = RawDatasetSchema.safeParse(minimal);
    expect(result.success).toBe(true);
  });
});

describe("SPENDEN_API_URL switch", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    delete process.env.SPENDEN_API_URL;
  });

  it("reads from the JSON fallback when SPENDEN_API_URL is unset", async () => {
    delete process.env.SPENDEN_API_URL;
    const fetchSpy = vi.fn();
    global.fetch = fetchSpy as unknown as typeof fetch;
    const { getSources: freshGetSources } = await import("./api");
    const sources = await freshGetSources();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(sources.some((s) => s.key === "reliefweb")).toBe(true);
  });

  it("prefers the live API and validates its response when SPENDEN_API_URL is set", async () => {
    process.env.SPENDEN_API_URL = "https://api.example.test";
    const live = [
      {
        id: "reliefweb",
        name: "ReliefWeb (live)",
        url: "https://reliefweb.int/",
        licence: "ReliefWeb terms of use",
        retrieved_at: "2026-08-29",
        default_verification: "third_party_reported",
      },
    ];
    const fetchSpy = vi.fn(async () => new Response(JSON.stringify(live), { status: 200 }));
    global.fetch = fetchSpy as unknown as typeof fetch;
    const { getSources: freshGetSources } = await import("./api");
    const sources = await freshGetSources();
    expect(fetchSpy).toHaveBeenCalledWith("https://api.example.test/v1/meta/sources");
    expect(sources).toEqual([
      {
        key: "reliefweb",
        name: "ReliefWeb (live)",
        url: "https://reliefweb.int/",
        licence: "ReliefWeb terms of use",
        retrieved_at: "2026-08-29",
      },
    ]);
  });

  it("throws a descriptive error when the live API returns a shape that fails validation", async () => {
    process.env.SPENDEN_API_URL = "https://api.example.test";
    const fetchSpy = vi.fn(async () => new Response(JSON.stringify([{ nonsense: true }]), { status: 200 }));
    global.fetch = fetchSpy as unknown as typeof fetch;
    const { getSources: freshGetSources } = await import("./api");
    await expect(freshGetSources()).rejects.toThrow(/failed schema validation/);
  });
});
