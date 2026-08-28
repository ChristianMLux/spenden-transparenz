import { useTranslations } from "next-intl";
import { Datum } from "@/components/datum/datum";
import type { Datum as DatumType, OrgDetail } from "@/lib/types";
import { OrgSection } from "./section";

const PRESENCE_ROW_CLASS = "flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1";
const PRESENCE_LABEL_CLASS = "w-full text-sm text-muted md:w-40 md:shrink-0";

/**
 * Section 3, "Präsenz in Nepal": a `<dl>` with since year, mode, staff count and
 * partners, one `<Datum variant="inline">` per row. Every row that carries an inline
 * datum is at least 44px tall (`min-h-11`) so the chip's expanded hit area cannot
 * overlap a neighbouring row's (DESIGN.md 7.6).
 */
export function PresenceSection({ org }: { org: OrgDetail }) {
  const t = useTranslations("org.presence");

  const modeRender = (value: string) => {
    const known = ["own_staff", "partners", "both", "unknown"];
    return known.includes(value) ? t(`modeValue.${value}`) : value;
  };

  // `partners` is a list, not a single Datum, so it has no gap_reason of its own. An
  // empty list is honestly a gap: most zero-partner orgs in the pilot data record
  // "nepal_presence.partners" as a searched-and-empty data_gap; where that record is
  // absent this reads as not yet searched rather than claiming a search that may not
  // have happened.
  const partnersGap: DatumType<string> = {
    value: null,
    is_gap: true,
    source_url: null,
    publisher: null,
    retrieved_at: org.last_updated,
    published_at: null,
    verification: "unverified",
    quote: null,
    note: null,
    gap_reason: org.data_gaps.some((g) => g.includes("nepal_presence.partners"))
      ? "searched_not_found"
      : "not_searched",
  };

  return (
    <OrgSection headingId="presence-heading" heading={t("heading")} label={t("label")}>
      <dl className="flex flex-col gap-3">
        <div className={PRESENCE_ROW_CLASS}>
          <dt className={PRESENCE_LABEL_CLASS}>{t("sinceYear")}</dt>
          <dd>
            <Datum
              datum={org.presence.since_year}
              field={t("sinceYear")}
              variant="inline"
              id="presence-since-year"
            />
          </dd>
        </div>

        <div className={PRESENCE_ROW_CLASS}>
          <dt className={PRESENCE_LABEL_CLASS}>{t("mode")}</dt>
          <dd>
            <Datum
              datum={org.presence.mode}
              field={t("mode")}
              variant="inline"
              render={modeRender}
              id="presence-mode"
            />
          </dd>
        </div>

        <div className={PRESENCE_ROW_CLASS}>
          <dt className={PRESENCE_LABEL_CLASS}>{t("staffCount")}</dt>
          <dd>
            <Datum
              datum={org.presence.staff_count}
              field={t("staffCount")}
              variant="inline"
              id="presence-staff-count"
            />
          </dd>
        </div>

        {org.presence.partners.length > 0 ? (
          org.presence.partners.map((partner, index) => (
            <div key={`partner-${index}`} className={PRESENCE_ROW_CLASS}>
              <dt className={PRESENCE_LABEL_CLASS}>{index === 0 ? t("partners") : null}</dt>
              <dd>
                <Datum
                  datum={partner}
                  field={t("partners")}
                  variant="inline"
                  id={`partner-${index}`}
                />
              </dd>
            </div>
          ))
        ) : (
          <div className={PRESENCE_ROW_CLASS}>
            <dt className={PRESENCE_LABEL_CLASS}>{t("partners")}</dt>
            <dd>
              <Datum
                datum={partnersGap}
                field={t("partners")}
                variant="inline"
                id="partners-gap"
              />
            </dd>
          </div>
        )}
      </dl>
    </OrgSection>
  );
}
