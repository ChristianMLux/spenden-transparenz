import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import type { Crisis } from "@/lib/types";
import { LocaleSwitch } from "./locale-switch";

/**
 * Not sticky: it would cost vertical space at 360px and buy nothing on a reading page
 * (DESIGN.md 8.1). This is Variant C's one structural move: a full-bleed dark navy band,
 * the same chrome surface the figure strip and filter rail continue below it. The
 * wordmark is white; the crisis name and GLIDE id sit in the chrome's muted tone so the
 * wordmark stays the loudest thing in the band.
 *
 * "Ich möchte helfen" (board.help.navLabel) is a plain link to the board's own #helfen
 * landmark, never a same-page anchor computed differently per route: from the board
 * page it is a same-document jump, from every other page (including an organisation
 * page, which carries its own per-org donation section) it is a normal navigation. Both
 * are the same href, so this header needs no per-route branching.
 */
export function SiteHeader({ crisis, siteName }: { crisis: Crisis; siteName: string }) {
  const locale = useLocale() as Locale;
  const t = useTranslations("common");
  const tBoard = useTranslations("board");
  const helpHref = `/${locale}${routing.pathnames["/krise/[crisis]"][locale].replace("[crisis]", crisis.slug)}#helfen`;

  return (
    <header className="bg-chrome text-chrome-ink print:hidden">
      <div className="mx-auto flex min-h-16 max-w-[80rem] flex-wrap items-center justify-between gap-x-6 gap-y-1 px-4 py-3">
        <p className="text-sm font-semibold text-chrome-ink">{siteName}</p>
        <p className="flex flex-wrap items-baseline gap-2">
          <span className="text-sm text-chrome-muted">
            {locale === "de" ? crisis.name_de : crisis.name_en}
          </span>
          <code className="font-mono text-xs text-chrome-muted">{crisis.glide_id}</code>
        </p>
        <div className="flex flex-wrap items-center gap-4">
          <a
            href={helpHref}
            className="flex min-h-11 items-center text-sm text-chrome-ink underline underline-offset-2"
          >
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
    </header>
  );
}
