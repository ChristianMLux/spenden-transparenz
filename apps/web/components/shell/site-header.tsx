import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import type { Crisis } from "@/lib/types";
import { LocaleSwitch } from "./locale-switch";

/**
 * Not sticky: it would cost vertical space at 360px and buy nothing on a reading page.
 * No logo, no search, no menu. The crisis and its GLIDE id are the identity.
 */
export function SiteHeader({ crisis, siteName }: { crisis: Crisis; siteName: string }) {
  const locale = useLocale() as Locale;
  const t = useTranslations("common");

  return (
    <header className="border-b border-rule print:hidden">
      <div className="mx-auto flex max-w-[80rem] flex-wrap items-baseline justify-between gap-2 px-4 py-3">
        <p className="text-sm">{siteName}</p>
        <p className="flex flex-wrap items-baseline gap-2">
          <span className="text-sm">{locale === "de" ? crisis.name_de : crisis.name_en}</span>
          <code className="font-mono text-xs text-muted">{crisis.glide_id}</code>
        </p>
        <LocaleSwitch
          current={locale}
          locales={routing.locales}
          navLabel={t("locale.label")}
          labels={Object.fromEntries(routing.locales.map((l) => [l, t(`locale.${l}`)]))}
        />
      </div>
    </header>
  );
}
