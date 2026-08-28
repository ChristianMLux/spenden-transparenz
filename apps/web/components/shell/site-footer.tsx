import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import { ThemeToggle } from "./theme-toggle";

const PAGES = [
  { key: "methodik", href: "/methodik" },
  { key: "quellen", href: "/quellen" },
  { key: "korrekturen", href: "/korrekturen" },
  { key: "impressum", href: "/impressum" },
  { key: "datenschutz", href: "/datenschutz" },
] as const;

export function SiteFooter({ generatedAt }: { generatedAt: string }) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;

  return (
    <footer className="mt-8 border-t border-rule print:hidden">
      <div className="mx-auto flex max-w-[80rem] flex-col gap-2 px-4 py-4 text-sm">
        <p className="text-xs text-muted">
          {t("footer.dataStand", { date: formatDate(generatedAt.slice(0, 10), locale) })}
        </p>
        <nav aria-label={t("mainLabel")}>
          <ul className="flex flex-wrap gap-4">
            {PAGES.map((page) => (
              <li key={page.key}>
                <Link href={page.href} className="underline">
                  {t(`footer.${page.key}`)}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        {/* The standing sentence. It is the product's whole claim, so it is on every page. */}
        <p className="max-w-[68ch] text-xs text-muted">{t("footer.standing")}</p>
        <ThemeToggle
          legend={t("theme.label")}
          labels={{
            system: t("theme.system"),
            light: t("theme.light"),
            dark: t("theme.dark"),
          }}
        />
      </div>
    </footer>
  );
}
