import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Crisis } from "@/lib/types";
import { LocaleSwitch } from "./locale-switch";

/** The board's localised path plus the help section's anchor, built the same way
 * board-labels.ts builds sourcesHref: read straight from routing.pathnames rather than
 * a client-side pathname API, since it is computed here, server-side, from data this
 * component already has (crisis.slug, locale). Works from any page, not just the board
 * itself, since the masthead renders on all of them. */
function helpHref(locale: Locale, crisisSlug: string): string {
  const path = routing.pathnames["/krise/[crisis]"][locale].replace("[crisis]", crisisSlug);
  return `/${locale}${path}#helfen`;
}

/**
 * The masthead. Two tiers, per BRIEF ("Amtsblatt"):
 *
 * 1. The band itself: full-bleed --band fill, ~64px, sticky (only this tier scrolls
 *    with the page; the sub-strip below it is normal flow, which keeps the sticky
 *    element cheap and avoids stacking two sticky offsets). The wordmark is the site's
 *    own identity, white on the band; the language switch sits opposite it.
 * 2. A thin sub-strip on the single warm tint, carrying the crisis title, its GLIDE id
 *    in mono, and the data-stand timestamp: the same three facts a printed register
 *    would put on its cover page. This is presentational text, not a heading.
 *
 *    On the board itself the crisis title is redundant with the page's own <h1> (see
 *    app/[locale]/krise/[crisis]/page.tsx) a few dozen pixels below it, so the strip
 *    drops its name there and keeps only the GLIDE id and the data stand; every other
 *    page has no <h1> naming the crisis, so the strip keeps the name. `.masthead-crisis-
 *    name`'s `body:has(#board-page) ...' rule in globals.css makes that call in pure
 *    CSS: the layout that renders this header sits above /krise/[crisis] in the route
 *    tree and has no prop-based way to know which page asked for it (any real one would
 *    mean either a client pathname read, which risks a post-hydration layout shift, or
 *    moving the header out of the shared layout into every page). `:has()` resolves
 *    from the already-server-rendered DOM at first paint, so there is no client
 *    JavaScript and no shift either way.
 */
export function SiteHeader({
  crisis,
  siteName,
  generatedAt,
}: {
  crisis: Crisis;
  siteName: string;
  generatedAt: string;
}) {
  const locale = useLocale() as Locale;
  const t = useTranslations("common");
  const tBoard = useTranslations("board");

  return (
    <header className="sticky top-0 z-40 print:hidden">
      <div className="masthead-band w-full bg-band">
        <div className="mx-auto flex max-w-[80rem] flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3 text-white">
          <p className="text-lg font-semibold">{siteName}</p>
          <div className="flex flex-wrap items-center gap-4">
            {/* Jumps to the help section on the board (BRIEF, action path, item a). A
                plain anchor, not @/i18n/navigation's Link: this renders on every page,
                and the pathname-translation runtime it would pull in is not otherwise
                paid for outside the board itself. */}
            <a href={helpHref(locale, crisis.slug)} className="flex min-h-11 items-center text-white underline">
              {tBoard("help.navLabel")}
            </a>
            <LocaleSwitch
              current={locale}
              locales={routing.locales}
              navLabel={t("locale.label")}
              labels={Object.fromEntries(routing.locales.map((l) => [l, t(`locale.${l}`)]))}
            />
          </div>
        </div>
      </div>
      <div className="w-full border-b border-rule bg-tint">
        <div className="mx-auto flex max-w-[80rem] flex-wrap items-baseline gap-x-2 gap-y-1 px-4 py-2 text-sm text-ink">
          <span className="masthead-crisis-name flex flex-wrap items-baseline gap-x-2">
            <span>{locale === "de" ? crisis.name_de : crisis.name_en}</span>
            <span className="text-muted">·</span>
          </span>
          <code className="font-mono text-xs text-muted">{crisis.glide_id}</code>
          <span className="text-muted">·</span>
          <span className="text-xs text-muted">
            {t("footer.dataStand", { date: formatDate(generatedAt.slice(0, 10), locale) })}
          </span>
        </div>
      </div>
    </header>
  );
}
