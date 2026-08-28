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
    <OrgSection headingId="gaps-heading" heading={t("heading")} label={t("label")}>
      {org.data_gaps.length === 0 ? (
        <p className="text-base text-ink">{t("empty")}</p>
      ) : (
        <div className="flex flex-col gap-4">
          {GAP_REASON_ORDER.filter((reason) => groups[reason].length > 0).map((reason) => (
            <div key={reason}>
              <h3 className="text-base text-ink">{t(`groupHeading.${reason}`)}</h3>
              {/* Two-column list per the variant brief: a CSS multi-column flow rather
                  than a grid, since entries are single sentences of uneven length, not
                  paired data. break-inside-avoid on each entry stops a sentence
                  splitting across the column gap. */}
              <ul className="mt-1 list-disc gap-x-8 pl-5 md:columns-2">
                {groups[reason].map((gap) => {
                  const { text, english } = sentenceFor(gap);
                  return (
                    <li key={gap} className="mb-1 break-inside-avoid text-sm text-ink">
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
