import { useTranslations } from "next-intl";
import type { OrgDetail } from "@/lib/types";
import { GAP_REASON_ORDER, groupDataGaps } from "./gap-reason";
import { OrgSection } from "./section";

/**
 * Section 7, "Was wir nicht wissen": `data_gaps` and `research_notes`, open, one
 * sentence per gap, grouped by the resolved gap_reason. Never an accordion, never
 * collapsed, never truncated (brief, verbatim) — this uses a plain `<ul>` under a plain
 * `<h3>` per group, nothing that can be closed.
 */
export function GapsSection({ org }: { org: OrgDetail }) {
  const t = useTranslations("org.gaps");
  const groups = groupDataGaps(org.data_gaps, org);

  return (
    <OrgSection headingId="gaps-heading" heading={t("heading")}>
      {org.data_gaps.length === 0 ? (
        <p className="text-base text-ink">{t("empty")}</p>
      ) : (
        <div className="flex flex-col gap-4">
          {GAP_REASON_ORDER.filter((reason) => groups[reason].length > 0).map((reason) => (
            <div key={reason}>
              <h3 className="text-base text-ink">{t(`groupHeading.${reason}`)}</h3>
              <ul className="mt-1 flex list-disc flex-col gap-1 pl-5">
                {groups[reason].map((gap) => (
                  <li key={gap} className="max-w-[68ch] text-sm text-ink">
                    {gap}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {org.research_notes ? (
        <div className="mt-4">
          <h3 className="text-base text-ink">{t("researchNotesHeading")}</h3>
          <p className="mt-1 max-w-[68ch] text-sm text-ink">{org.research_notes}</p>
        </div>
      ) : null}
    </OrgSection>
  );
}
