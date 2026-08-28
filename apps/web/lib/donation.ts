import type { DonationChannel, DonationLink } from "./types";

/**
 * The three honest states of an official donation channel, and the strings each one
 * resolves to. This module is deliberately headless: it decides *what a reader is told*
 * about a donation channel, and nothing about how it looks. The three WP4 visual
 * variants render it differently, but none of them may say anything different.
 *
 * Why that split matters here more than anywhere else in the app: this is the one field
 * that could tip an information layer into a recommendation. Keeping the vocabulary in a
 * single tested function means "kein offizieller Spendenweg gefunden" cannot quietly
 * become a softer or smaller sentence in one variant, and no variant can invent a
 * call to action of its own.
 */
export type DonationState = "found" | "not_found" | "not_searched";

export interface DonationView {
  state: DonationState;
  /** The organisation's own page. Non-null exactly when state is "found". */
  href: string | null;
  /** Host shown next to the link, e.g. "donation.nrcs.org". */
  publisher: string | null;
  retrieved_at: string | null;
  /** Key under common.datum.word: the provenance word, "Eigenangabe" for a found page. */
  verificationKey: string;
  /** Key under common.donation: the label a reader sees. */
  labelKey: "label" | "notFound" | "notSearched";
  /** Key under common.donation.scope, or null when there is no page to describe. */
  scopeKey: "flood" | "general" | null;
  /** The source sentence behind the claim, when the research recorded one. */
  quote: string | null;
}

function hostOf(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

export function donationView(channel: DonationLink & Partial<DonationChannel>): DonationView {
  const common = {
    // Derived rather than sent: the host is already in the url, and 44 copies of it
    // are payload the board does not have to pay for.
    publisher: channel.publisher ?? hostOf(channel.url),
    retrieved_at: channel.retrieved_at,
    verificationKey: channel.verification,
    quote: channel.quote ?? null,
  };

  if (channel.url) {
    return {
      ...common,
      state: "found",
      href: channel.url,
      labelKey: "label",
      // flood_specific is a boolean on every found channel; null would be a data defect,
      // and "general" is the weaker of the two claims, so it is the safe reading.
      scopeKey: channel.flood_specific === true ? "flood" : "general",
    };
  }

  // "We did not look" and "we looked and found nothing" are different statements about
  // different things, exactly as gap_reason is everywhere else in this product.
  const searched = channel.gap_reason !== "not_searched";
  return {
    ...common,
    state: searched ? "not_found" : "not_searched",
    href: null,
    labelKey: searched ? "notFound" : "notSearched",
    scopeKey: null,
  };
}
