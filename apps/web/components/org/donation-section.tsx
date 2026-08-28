import { useTranslations } from "next-intl";
import { DonationLine } from "@/components/donation/donation-line";
import { donationView } from "@/lib/donation";
import type { OrgDetail } from "@/lib/types";
import { OrgSection } from "./section";

/**
 * "Spenden an diese Organisation", directly under the identity panel (variant brief).
 * Shares lib/donation.ts with the board record and the government-fund entries in the
 * board's help section — one headless source of truth, three renderings, none of them
 * allowed to say anything different from the other two.
 *
 * No `label` prop here (unlike the other seven sections): a new label word would be new
 * donation copy, and the base branch is explicit that this variant writes none — it asks
 * rather than invents. Flagged to the lead in the worker report instead of guessed at.
 */
export function DonationSection({ org }: { org: OrgDetail }) {
  const t = useTranslations("org.donation");
  const tCommon = useTranslations("common");
  const view = donationView(org.donation);

  return (
    <OrgSection headingId="donation-heading" heading={t("heading")}>
      <div className="flex flex-col gap-2">
        {view.state === "found" ? (
          <>
            <DonationLine view={view} />
            {view.scopeKey ? (
              <p className="text-sm text-muted">{tCommon(`donation.scope.${view.scopeKey}`)}</p>
            ) : null}
          </>
        ) : (
          <>
            <p className="max-w-[68ch] text-base text-ink">{t("empty")}</p>
            <DonationLine view={view} />
          </>
        )}
        <p className="max-w-[68ch] text-sm text-muted">{tCommon("donation.safety")}</p>
      </div>
    </OrgSection>
  );
}
