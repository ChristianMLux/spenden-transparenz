import { useTranslations } from "next-intl";
import { DonationLine } from "@/components/shared/donation-line";
import type { GovernmentFund } from "@/lib/types";

/**
 * "Ich möchte helfen" (BRIEF, action path, item a/e). The masthead's new nav entry
 * jumps here via #helfen. This section is also where the page's opening scope
 * statement now lives: board.help.line1/line2 say almost exactly what the old
 * scopeLine1/scopeLine2 paragraph said, so that paragraph was removed from the page
 * body rather than stacking a second, near-duplicate sentence above this one (the page
 * says it once, per the lead's instruction).
 *
 * The government fund sits here, never in the organisation list: it is not one of the
 * 44 organisations, and putting it there would corrupt "44 von 44 Organisationen",
 * every facet count and "9 ohne gefundene Reaktion" (board.help.governmentNote says as
 * much). It gets the identical DonationLine treatment every organisation's channel
 * gets — same component, same classes, so it cannot read as more or less official than
 * one of the 44.
 *
 * Kept deliberately compact because e2e/board-fold.spec.ts requires the first
 * organisation to stay visible above y=500 at 1280x900, and this section sits above the
 * figure strip and the list, in the same vertical budget. The 68ch reading-comfort
 * measure DESIGN.md uses for body prose is deliberately dropped here: this is a compact
 * information panel a reader skims once, not a paragraph meant to be read start to
 * finish, and at 68ch the three combined sentences wrapped to five or six lines and blew
 * the fold budget by itself. One flowing paragraph (not three separate blocks) and the
 * government fund folded onto two lines, not four, do the rest of the saving.
 */
export function HelpSection({ governmentFunds }: { governmentFunds: GovernmentFund[] }) {
  const t = useTranslations("board");
  const fund = governmentFunds[0];

  return (
    <section
      id="helfen"
      aria-labelledby="helfen-heading"
      className="border-l-[3px] border-accent bg-tint p-1"
    >
      <h2 id="helfen-heading" className="text-xs text-ink">
        {t("help.heading")}
      </h2>
      <p className="mt-0.5 text-sm text-ink">
        {t("help.line1")} {t("help.line2")} {t("help.line3")}
      </p>
      {fund ? (
        <p className="mt-0.5 flex flex-wrap items-baseline gap-x-2 gap-y-1 text-xs text-ink">
          <span className="text-muted">{t("help.governmentHeading")}:</span>
          <span>{fund.name}</span>
          <DonationLine channel={fund} />
          <span className="text-muted">{t("help.governmentNote")}</span>
        </p>
      ) : null}
    </section>
  );
}
