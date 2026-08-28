import { useLocale, useTranslations } from "next-intl";
import { Datum } from "@/components/datum/datum";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Registration } from "@/lib/types";
import { OrgSection } from "./section";
import { registryDomain } from "./registry-meta";

const KNOWN_REGISTRIES = new Set([
  "NP_SWC",
  "NP_DAO",
  "IATI",
  "US_IRS",
  "DE_DZI",
  "DE_ITZ",
  "DE_VEREINSREGISTER",
  "UK_CC",
  "CH_ZEWO",
  "UN",
  "OTHER",
]);

/**
 * Section 4, "Registrierungen und Kennungen": the section that decides whether the page
 * is honest. 56 of 75 rows in the pilot data carry no identifier (DESIGN.md 4), so this
 * is a sentence list, never a table of dashes: every registry gets its full name as a
 * `<dt>`, and a `<dd>` that either shows the identifier or spells out what was looked for
 * and why it is not there. The IATI row is distinguished by an explanatory sentence, not
 * by colour, because it is the join key across datasets. This is also the page's one
 * horizontal scroll box, for identifiers that do not fit at 360px.
 */
export function RegistrationsSection({ registrations }: { registrations: Registration[] }) {
  const t = useTranslations("org.registrations");
  const locale = useLocale() as Locale;

  const registryName = (registry: string) =>
    KNOWN_REGISTRIES.has(registry) ? t(`registry.${registry}`) : registry;

  const gapSentence = (registration: Registration): string => {
    const { datum, registry } = registration;
    const name = registryName(registry);
    const domain = registryDomain(registry);
    const date = datum.retrieved_at ? formatDate(datum.retrieved_at, locale) : null;

    if (datum.gap_reason === "not_searched") {
      return t("sentence.not_searched", { registry: name });
    }
    if (datum.gap_reason === "source_unreachable") {
      if (domain && date) return t("sentence.sourceUnreachableWithDomain", { domain, date });
      if (date) return t("sentence.sourceUnreachable", { date });
      return t("sentence.sourceUnreachablePlain");
    }
    if (datum.gap_reason === "not_public") {
      return t("sentence.notPublic");
    }
    // searched_not_found, or a gap with no reason recorded: the honest default.
    return domain && date
      ? t("sentence.searchedNotFoundWithDomain", { domain, date })
      : t("sentence.searchedNotFound", { registry: name });
  };

  return (
    <OrgSection headingId="registrations-heading" heading={t("heading")} label={t("label")}>
      <dl className="flex flex-col gap-4">
        {registrations.map((registration, index) => {
          const name = registryName(registration.registry);
          const isIati = registration.registry === "IATI";
          return (
            <div key={`${registration.registry}-${index}`} className="flex flex-col gap-1">
              <dt className="text-base text-ink">{name}</dt>
              <dd className="flex flex-col gap-1">
                {registration.datum.value ? (
                  // The only place a value can be a long, unbreakable string (an
                  // identifier, not prose), so this is the only place that scrolls
                  // sideways rather than wrapping: DESIGN.md's single horizontal scroll
                  // box for the page, scoped to exactly where it can occur. Wrapping the
                  // whole section in this instead forced every honest sentence below to
                  // stop wrapping too (caught in a 360px screenshot review).
                  <div className="overflow-x-auto overscroll-x-contain">
                    <div className="flex min-h-11 w-max flex-wrap items-center gap-2">
                      <Datum
                        datum={registration.datum}
                        field={name}
                        variant="inline"
                        id={`registration-${index}`}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1">
                    <p className="max-w-[68ch] text-base text-ink">{gapSentence(registration)}</p>
                    <div className="flex min-h-11 flex-wrap items-center gap-2">
                      <Datum
                        datum={registration.datum}
                        field={name}
                        variant="inline"
                        render={() => null}
                        id={`registration-${index}`}
                      />
                    </div>
                  </div>
                )}
                {isIati ? <p className="text-sm text-muted">{t("iatiNote")}</p> : null}
              </dd>
            </div>
          );
        })}
      </dl>
    </OrgSection>
  );
}
