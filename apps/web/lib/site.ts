// Shared by every WP3 page, sitemap.ts, robots.ts and opengraph-image.tsx: one place
// that turns an app-internal pathname into the absolute, locale-prefixed URL search
// engines and `alternates.languages` need. No production domain is decided yet (see
// DESIGN.md 12.2, "Offene Punkte an den PO"); NEXT_PUBLIC_SITE_URL overrides the
// placeholder once one is.
import { getPathname } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://spenden-transparenz.org").replace(
  /\/$/,
  "",
);

// Reuses next-intl's own inferred href type (a plain pathname for static routes, or
// `{ pathname, params }` for one with a dynamic segment such as "/organisation/[orgId]")
// instead of redeclaring the typed-pathnames generic by hand.
type Href = Parameters<typeof getPathname>[0]["href"];

/** Absolute, locale-prefixed URL for one of this app's own pathnames (see i18n/routing.ts). */
export function urlFor(href: Href, locale: Locale): string {
  return `${SITE_URL}${getPathname({ href, locale })}`;
}

/** { de: absoluteUrl, en: absoluteUrl }, the shape next/metadata wants for `alternates.languages`. */
export function alternateLanguages(href: Href): Record<Locale, string> {
  return Object.fromEntries(routing.locales.map((locale) => [locale, urlFor(href, locale)])) as Record<
    Locale,
    string
  >;
}
