import { useLocale, useTranslations } from "next-intl";
import { Datum } from "@/components/datum/datum";
import type { Locale } from "@/i18n/routing";
import { domainOf, formatDate } from "@/lib/format";
import type { OrgDetail } from "@/lib/types";
import { OrgSection } from "./section";
import { SourceToggleButton } from "./source-toggle";

/**
 * Section 1, "Kopf": name, the Devanagari name where one was found, aliases, type, seat,
 * website with a visible domain, last updated, and the source-visibility switch. No
 * score, no badge row, no summary line (brief, verbatim).
 *
 * `legal_name` is part of `OrgDetail` but no section of the brief names a place to show
 * it; it is left undisplayed here rather than given an invented slot, and its gap still
 * surfaces honestly through "Was wir nicht wissen" via `data_gaps`.
 */
export function OrgHeader({ org }: { org: OrgDetail }) {
  const t = useTranslations("org.header");
  const tCommon = useTranslations("common");
  const locale = useLocale() as Locale;

  const countryName = (code: string) => {
    try {
      return new Intl.DisplayNames([locale === "de" ? "de" : "en"], { type: "region" }).of(code) ?? code;
    } catch {
      return code;
    }
  };

  const seatText = org.hq_city
    ? t("seat", { place: `${org.hq_city}, ${countryName(org.hq_country)}` })
    : t("seatCountryOnly", { country: countryName(org.hq_country) });

  const websiteDomain = domainOf(org.website);

  return (
    <OrgSection
      first
      headingId="org-name"
      heading={org.name}
      headingClassName="text-xl"
      headingExtra={
        <SourceToggleButton
          showLabel={tCommon("sources.showAll")}
          hideLabel={tCommon("sources.hideAll")}
        />
      }
    >
      <dl className="flex flex-col gap-2 text-base text-ink">
        {org.local_script.value ? (
          <div className="flex min-h-11 flex-wrap items-center gap-2">
            <dd className="flex flex-wrap items-center gap-2 text-xl">
              <span lang="ne">{org.local_script.value}</span>
              <Datum
                datum={org.local_script}
                field={t("localScriptField")}
                variant="inline"
                render={() => null}
                id="local-script"
              />
            </dd>
          </div>
        ) : null}

        {org.aliases.length > 0 ? (
          <div>
            <dt className="inline text-sm text-muted">{t("aliasesLabel")}: </dt>
            <dd className="inline">{org.aliases.join(", ")}</dd>
          </div>
        ) : null}

        <div>
          <dd>{tCommon(`orgType.${org.org_type}`)}</dd>
        </div>

        <div>
          <dd>{seatText}</dd>
        </div>

        {org.website ? (
          <div>
            <dt className="sr-only">{t("website")}</dt>
            <dd>
              <a href={org.website} rel="noopener" className="underline">
                {websiteDomain ?? org.website}
              </a>
            </dd>
          </div>
        ) : null}

        <div className="text-sm text-muted">
          <dd>{t("lastUpdated", { date: formatDate(org.last_updated, locale) })}</dd>
        </div>
      </dl>
    </OrgSection>
  );
}
