import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import { NOW } from "@/lib/now";
import { OrgSection } from "./section";

// No corrections contact address exists anywhere in the repo yet (checked: no mailto,
// no contact@ string in any file). Impressum and Datenschutz already ship with a visible
// "content pending from Chris" placeholder per DESIGN.md 8.4; this follows the same
// pattern rather than inventing a real-looking address silently. Report to the lead.
const CORRECTIONS_EMAIL = "korrekturen@spenden-transparenz.de";

/**
 * Section 8, "Fehler gefunden?": one sentence, a link to /korrekturen, and a mailto with
 * the org id and today's date pre-filled in the subject so reports are traceable.
 */
export function CorrectionsLink({ orgId }: { orgId: string }) {
  const t = useTranslations("org.corrections");
  const locale = useLocale() as Locale;
  const date = formatDate(NOW.toISOString().slice(0, 10), locale);
  const subject = t("mailSubject", { orgId, date });
  const mailtoHref = `mailto:${CORRECTIONS_EMAIL}?subject=${encodeURIComponent(subject)}`;

  return (
    <OrgSection headingId="corrections-heading" heading={t("heading")} label={t("label")}>
      <p className="max-w-[68ch] text-base text-ink">{t("sentence")}</p>
      <p className="mt-2 flex flex-wrap gap-4 text-sm">
        <Link href="/korrekturen" className="underline">
          {t("linkLabel")}
        </Link>
        <a href={mailtoHref} className="underline">
          {t("mailLabel")}
        </a>
      </p>
    </OrgSection>
  );
}
