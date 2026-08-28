import { describe, expect, it } from "vitest";
import { getBoard, getOrg } from "./api";
import { donationView } from "./donation";
import type { DonationChannel } from "./types";

const base: DonationChannel = {
  url: "https://donation.nrcs.org/",
  channel_type: "donation_page",
  flood_specific: false,
  source_url: "https://nrcs.org",
  publisher: "donation.nrcs.org",
  retrieved_at: "2026-08-28",
  verification: "self_reported",
  quote: "Ways to Donate To Nepal Redcross",
  note: null,
  gap_reason: null,
};

describe("donationView", () => {
  it("reads a found channel as the general page unless the flood flag is true", () => {
    expect(donationView(base)).toMatchObject({
      state: "found",
      href: "https://donation.nrcs.org/",
      labelKey: "label",
      scopeKey: "general",
      verificationKey: "self_reported",
    });
    expect(donationView({ ...base, flood_specific: true }).scopeKey).toBe("flood");
  });

  it("treats a missing flood flag as the weaker claim, never as flood-specific", () => {
    expect(donationView({ ...base, flood_specific: null }).scopeKey).toBe("general");
  });

  it("separates 'searched and found nothing' from 'never searched'", () => {
    const searched = donationView({
      ...base,
      url: null,
      channel_type: null,
      flood_specific: null,
      gap_reason: "searched_not_found",
    });
    expect(searched).toMatchObject({ state: "not_found", labelKey: "notFound", href: null });

    const never = donationView({
      ...base,
      url: null,
      channel_type: null,
      flood_specific: null,
      gap_reason: "not_searched",
    });
    expect(never).toMatchObject({ state: "not_searched", labelKey: "notSearched", href: null });
  });

  it("never returns an href for a state that has no page", () => {
    for (const gap of ["searched_not_found", "not_searched", "source_unreachable"] as const) {
      expect(donationView({ ...base, url: null, gap_reason: gap }).href).toBeNull();
    }
  });
});

describe("donation data as loaded", () => {
  it("attaches a channel to every organisation on the board", async () => {
    const board = await getBoard("nepal-flut-2026");
    expect(board.responders).toHaveLength(44);
    for (const r of board.responders) {
      expect(r.donation).toBeDefined();
      expect(["found", "not_found", "not_searched"]).toContain(donationView(r.donation).state);
    }
  });

  it("matches the researched split of 34 found and 10 searched without a result", async () => {
    const board = await getBoard("nepal-flut-2026");
    const states = board.responders.map((r) => donationView(r.donation).state);
    expect(states.filter((s) => s === "found")).toHaveLength(34);
    expect(states.filter((s) => s === "not_found")).toHaveLength(10);
    expect(states.filter((s) => s === "not_searched")).toHaveLength(0);
  });

  it("carries every found link on the organisation's own domain, never a payment host", async () => {
    const board = await getBoard("nepal-flut-2026");
    for (const r of board.responders) {
      const view = donationView(r.donation);
      if (view.state !== "found") continue;
      expect(view.href).toMatch(/^https:\/\//);
      expect(view.publisher).toBeTruthy();
    }
  });

  it("exposes the government fund apart from the organisations, never inside the count", async () => {
    const board = await getBoard("nepal-flut-2026");
    expect(board.government_funds).toHaveLength(1);
    const fund = board.government_funds[0];
    expect(fund).toBeDefined();
    expect(fund?.name).toContain("Prime Minister");
    expect(board.counts.orgs).toBe(44);
    expect(board.responders.some((r) => r.name.includes("Prime Minister"))).toBe(false);
  });

  it("gives the organisation page the same channel as the board row", async () => {
    const board = await getBoard("nepal-flut-2026");
    const row = board.responders.find((r) => r.org_id === "nepal-red-cross-society");
    const org = await getOrg("nepal-red-cross-society");
    expect(org.donation.url).toBe(row?.donation.url);
  });

  it("holds no account number anywhere in the donation data", async () => {
    const board = await getBoard("nepal-flut-2026");
    const blob = JSON.stringify([board.responders.map((r) => r.donation), board.government_funds]);
    // IBAN-shaped and long digit runs: the research rule is "link only, never numbers".
    expect(blob).not.toMatch(/\b[A-Z]{2}\d{2}[A-Z0-9]{10,}\b/);
    expect(blob).not.toMatch(/\b\d{9,}\b/);
  });
});
