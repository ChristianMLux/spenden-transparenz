import { useTranslations } from "next-intl";
import { DonationLine } from "@/components/shared/donation-line";
import { donationView } from "@/lib/donation";
import type { OrgDetail } from "@/lib/types";
import { OrgSection } from "./section";

/**
 * "Spenden an diese Organisation" (BRIEF, action path, item c), directly under the
 * identity header. The link and its provenance chip are DonationLine — the same
 * component the board row and the government fund use, so the channel reads identically
 * everywhere it appears. The flood-specific distinction is scopeKey rendered as words
 * (common.donation.scope.flood/general), never a badge or a colour: a second visual
 * signal here would read as a quality marker, which this field is not allowed to be.
 * The safety line renders verbatim regardless of state, because "check the bank details
 * yourself" is good advice whether or not a channel was found.
 */
export function DonationSection({ donation }: { donation: OrgDetail["donation"] }) {
  const t = useTranslations("org.donation");
  const tCommon = useTranslations("common");
  const view = donationView(donation);

  return (
    <OrgSection headingId="donation-heading" heading={t("heading")}>
      <div className="flex flex-col gap-2">
        {view.state !== "found" ? (
          <p className="max-w-[68ch] text-base text-ink">{t("empty")}</p>
        ) : null}
        <div>
          <DonationLine channel={donation} />
        </div>
        {view.scopeKey ? (
          <p className="text-sm text-muted">{tCommon(`donation.scope.${view.scopeKey}`)}</p>
        ) : null}
        <p className="text-sm text-muted">{tCommon("donation.safety")}</p>
      </div>
    </OrgSection>
  );
}
