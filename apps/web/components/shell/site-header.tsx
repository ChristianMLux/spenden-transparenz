import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Crisis } from "@/lib/types";
import { LocaleSwitch } from "./locale-switch";

/**
 * The masthead. Two tiers, per BRIEF ("Amtsblatt"):
 *
 * 1. The band itself: full-bleed --band fill, ~64px, sticky (only this tier scrolls
 *    with the page; the sub-strip below it is normal flow, which keeps the sticky
 *    element cheap and avoids stacking two sticky offsets). The wordmark is the site's
 *    own identity, white on the band; the language switch sits opposite it.
 * 2. A thin sub-strip on the single warm tint, carrying the crisis title, its GLIDE id
 *    in mono, and the data-stand timestamp: the same three facts a printed register
 *    would put on its cover page. This is presentational text, not a heading; the
 *    board page still carries the real <h1> for the crisis in its own content (see
 *    app/[locale]/krise/[crisis]/page.tsx), exactly as the pre-existing shell already
 *    separated "identity, shown everywhere" from "the page's own heading".
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

  return (
    <header className="sticky top-0 z-40 print:hidden">
      <div className="masthead-band w-full bg-band">
        <div className="mx-auto flex max-w-[80rem] items-center justify-between gap-4 px-4 py-3 text-white">
          <p className="text-lg font-semibold">{siteName}</p>
          <LocaleSwitch
            current={locale}
            locales={routing.locales}
            navLabel={t("locale.label")}
            labels={Object.fromEntries(routing.locales.map((l) => [l, t(`locale.${l}`)]))}
          />
        </div>
      </div>
      <div className="w-full border-b border-rule bg-tint">
        <div className="mx-auto flex max-w-[80rem] flex-wrap items-baseline gap-x-2 gap-y-1 px-4 py-2 text-sm text-ink">
          <span>{locale === "de" ? crisis.name_de : crisis.name_en}</span>
          <span className="text-muted">·</span>
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
