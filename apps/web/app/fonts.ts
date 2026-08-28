import { Noto_Sans_Devanagari, Public_Sans, Source_Serif_4 } from "next/font/google";

// next/font downloads these at build time and serves them from our own origin, so the
// site makes zero third-party requests and needs no cookie banner.
//
// Public Sans rather than Inter: it is the typeface of the U.S. Web Design System, so it
// carries the register, not the SaaS landing page, and it is narrower than Inter, which
// costs fewer line breaks in German compounds at 360px. See DESIGN.md 5.4.

export const serif = Source_Serif_4({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-source-serif",
});

export const sans = Public_Sans({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-public-sans",
});

// Four organisation records carry a Devanagari name. Loading this face eagerly would
// put a script nobody else needs into the budget of every page, so it is not preloaded
// and is applied only through :lang(ne).
export const devanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  display: "swap",
  variable: "--font-noto-devanagari",
  preload: false,
});

export const fontVariables = `${serif.variable} ${sans.variable} ${devanagari.variable}`;
