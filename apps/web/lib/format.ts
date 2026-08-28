import type { Locale } from "@/i18n/routing";

const DATE_FORMATS: Record<Locale, Intl.DateTimeFormatOptions> = {
  // 27.08.2026
  de: { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC" },
  // 27 Aug 2026. The month is spelled so that 08/07 is never read as August the 7th.
  en: { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" },
};

const LOCALE_TAGS: Record<Locale, string> = { de: "de-DE", en: "en-GB" };

/** Formats an ISO date. Always UTC, so the day never shifts under the reader's clock. */
export function formatDate(iso: string, locale: Locale): string {
  const d = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat(LOCALE_TAGS[locale], DATE_FORMATS[locale]).format(d);
}

/** Whole days between an ISO date and `now`. Negative for future dates. */
export function relativeDays(iso: string, now: Date): number {
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const then = new Date(`${iso}T00:00:00Z`).getTime();
  return Math.round((today - then) / 86_400_000);
}

/** The host a reader would recognise. Returns null rather than throwing or guessing. */
export function domainOf(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
