import { useLocale, useTranslations } from "next-intl";
import { DonationLine } from "@/components/donation/donation-line";
import type { Locale } from "@/i18n/routing";
import { donationView } from "@/lib/donation";
import type { OrgDetail } from "@/lib/types";
import { OrgSection } from "./section";

/**
 * "Spenden an diese Organisation", directly under the navy identity header (the next
 * OrgSection in document order, so it inherits the standard 3px accent rule + 32px gap
 * every section after the header already carries).
 *
 * Whether a channel was found or not, the section always closes with
 * common.donation.safety verbatim: a safety reminder, not a claim about this particular
 * organisation, so it belongs regardless of state. The flood-specific/general
 * distinction (scopeKey) is written out as a sentence, per the instruction that it is
 * never a badge or a colour.
 */
export function DonationSection({ donation }: { donation: OrgDetail["donation"] }) {
  const t = useTranslations("org.donation");
  const tCommon = useTranslations("common");
  const locale = useLocale() as Locale;
  const view = donationView(donation);

  return (
    <OrgSection headingId="donation-heading" heading={t("heading")}>
      <div className="flex flex-col gap-2">
        {view.state !== "found" ? (
          <p className="max-w-[68ch] text-base text-ink">{t("empty")}</p>
        ) : null}
        <div className="flex min-h-11 flex-wrap items-center gap-2">
          <DonationLine view={view} locale={locale} />
        </div>
        {view.state === "found" && view.scopeKey ? (
          <p className="text-sm text-muted">{tCommon(`donation.scope.${view.scopeKey}`)}</p>
        ) : null}
        <p className="max-w-[68ch] text-sm text-muted">{tCommon("donation.safety")}</p>
      </div>
    </OrgSection>
  );
}
