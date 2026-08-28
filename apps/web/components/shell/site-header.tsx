import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { ACTIVE_CRISIS, routing } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Crisis } from "@/lib/types";
import { LocaleSwitch } from "./locale-switch";

/**
 * Variant B ("Dossier") masthead: two stacked bands, not one row. Not sticky in either
 * band: it would cost vertical space at 360px and buy nothing on a reading page. No
 * logo, no search, no menu. The crisis and its GLIDE id are the identity.
 *
 * Band 1 (--masthead, a fixed dark ink-blue in both colour schemes, see globals.css)
 * carries the wordmark and the language switch, both forced to white — this is the
 * page's one constant brand mark. Band 2 sits on --surface, the same "one step lighter
 * than the page" tint every panel on this page uses, and carries the crisis title, the
 * GLIDE id and the data-stand timestamp. The <h1> for the crisis title still lives on
 * the page itself (DESIGN.md 8.2); this band repeats the same text as a label, not as a
 * second heading, so the document outline stays exactly what DESIGN.md specifies.
 *
 * Band 1 also carries the "Ich möchte helfen" entry (WP4 action-path addition): a plain
 * white link, same tier as the wordmark, that jumps to `#helfen` on the board — the
 * short, collapsed-by-default section built in krise/[crisis]/page.tsx. It renders on
 * every page, not only the board, because the destination is one fixed anchor and "how
 * do I help" is a fair question from any page on this site, not only the board.
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
  const helpHref = `/${locale}${routing.pathnames["/krise/[crisis]"][locale].replace("[crisis]", ACTIVE_CRISIS)}#helfen`;

  return (
    <header className="print:hidden">
      <div className="bg-masthead">
        {/* py-1, not py-3: the row's real height already comes from LocaleSwitch's own
            44px targets (min-h-11, a real WCAG tap-target requirement), so the outer
            padding is free to be thin without shrinking anything a reader has to tap.
            Trimmed as part of the board-fold budget (e2e/board-fold.spec.ts). */}
        <div className="mx-auto flex max-w-[80rem] flex-wrap items-center justify-between gap-2 px-4 py-1">
          <div className="flex flex-wrap items-center gap-4">
            <p className="text-sm text-white">{siteName}</p>
            <a href={helpHref} className="text-sm text-white underline underline-offset-2">
              {tBoard("help.navLabel")}
            </a>
          </div>
          <LocaleSwitch
            current={locale}
            locales={routing.locales}
            navLabel={t("locale.label")}
            labels={Object.fromEntries(routing.locales.map((l) => [l, t(`locale.${l}`)]))}
            inverted
          />
        </div>
      </div>
      <div className="border-b border-rule bg-surface">
        <div className="mx-auto flex max-w-[80rem] flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3">
          <p className="flex flex-wrap items-baseline gap-2">
            <span className="text-lg text-ink">{locale === "de" ? crisis.name_de : crisis.name_en}</span>
            <code className="font-mono text-xs text-muted">{crisis.glide_id}</code>
          </p>
          <p className="text-xs text-muted">
            {t("footer.dataStand", { date: formatDate(generatedAt.slice(0, 10), locale) })}
          </p>
        </div>
      </div>
    </header>
  );
}
