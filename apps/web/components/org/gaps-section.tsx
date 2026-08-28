import { useTranslations } from "next-intl";
import type { OrgDetail } from "@/lib/types";
import { gapLabel } from "./gap-label";
import { GAP_REASON_ORDER, groupDataGaps } from "./gap-reason";
import { OrgSection } from "./section";

const KNOWN_REGISTRIES = new Set([
  "NP_SWC",
  "NP_DAO",
  "NP_CDO",
  "UK_CC",
  "UK_OSCR",
  "US_IRS",
  "DE_VEREINSREGISTER",
  "DE_DZI",
  "DE_ITZ",
  "CH_ZEWO",
  "AT_OSGS",
  "IATI",
  "UN",
  "OTHER",
]);

/**
 * Section 7, "Was wir nicht wissen": `data_gaps` and `research_notes`, open, one sentence
 * per gap, grouped by the resolved gap_reason. Never an accordion, never collapsed, never
 * truncated (brief, verbatim) — a plain `<ul>` under a plain `<h3>` per group, nothing
 * that can be closed.
 *
 * Each entry goes through gapLabel() rather than being printed raw. The stored values are
 * JSON paths like `financial_transparency.income`, and answering "what do we not know"
 * with a database identifier is not an answer. Where the source appended an English
 * qualifier, it is kept and marked lang="en" instead of dropped: it is usually the most
 * specific thing we know about that particular gap.
 */
export function GapsSection({ org }: { org: OrgDetail }) {
  const t = useTranslations("org.gaps");
  const tReg = useTranslations("org.registrations");
  const groups = groupDataGaps(org.data_gaps, org);

  function sentenceFor(entry: string) {
    const label = gapLabel(entry);
    if (label.verbatim !== null) {
      return { text: null, english: label.verbatim };
    }
    const registry =
      label.registry && KNOWN_REGISTRIES.has(label.registry)
        ? tReg(`registry.${label.registry}`)
        : (label.registry ?? "");
    const text = label.key ? t(`path.${label.key}`, { registry }) : entry;
    return { text, english: label.qualifier };
  }

  return (
    <OrgSection headingId="gaps-heading" heading={t("heading")}>
      {org.data_gaps.length === 0 ? (
        <p className="text-base text-ink">{t("empty")}</p>
      ) : (
        // Two columns (BRIEF, "Amtsblatt"): a CSS grid rather than multi-column text, so
        // a group's own <h3> and <ul> never split across the column break the way
        // `columns-2` would risk with a group that starts near the bottom of one column.
        <div className="grid grid-cols-1 gap-x-8 gap-y-4 md:grid-cols-2">
          {GAP_REASON_ORDER.filter((reason) => groups[reason].length > 0).map((reason) => (
            <div key={reason}>
              <h3 className="text-base text-ink">{t(`groupHeading.${reason}`)}</h3>
              <ul className="mt-1 flex list-disc flex-col gap-1 pl-5">
                {groups[reason].map((gap) => {
                  const { text, english } = sentenceFor(gap);
                  return (
                    <li key={gap} className="max-w-[68ch] text-sm text-ink">
                      {text}
                      {english ? (
                        <>
                          {text ? " " : null}
                          <span lang="en">{english}</span>
                        </>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}

      {org.research_notes ? (
        <div className="mt-4">
          <h3 className="text-base text-ink">{t("researchNotesHeading")}</h3>
          {/* research_notes is source material and is always English. Marking the
              language stops a screen reader pronouncing it as German, and the
              introduction makes the switch deliberate rather than a leak. */}
          <p className="mt-1 text-sm text-muted">{t("researchNotesIntro")}</p>
          <p lang="en" className="mt-1 max-w-[68ch] text-sm text-ink">
            {org.research_notes}
          </p>
        </div>
      ) : null}
    </OrgSection>
  );
}
