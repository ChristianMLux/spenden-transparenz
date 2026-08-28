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
 * `legal_name` is shown here when it says something the common name does not. 37 of the
 * 44 records carry one, and a registered legal name is the most useful single fact for a
 * reader who wants to look the organisation up in a register themselves, which is what
 * this page exists to enable. It is suppressed when it merely repeats the common name,
 * because a line that says the same thing twice is noise, not information.
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
      label={t("label")}
      headingClassName="text-xl"
      headingExtra={
        <SourceToggleButton
          showLabel={tCommon("sources.showAll")}
          hideLabel={tCommon("sources.hideAll")}
        />
      }
    >
      {/* The identity header is the widest panel on the page (variant brief), so its
          facts run in a two-column meta grid rather than a single stacked list. The
          name in local script, the legal name and the alias line stay full width: they
          are either display text or a sentence, and squeezing either into a half column
          reads worse than the extra height of leaving them be. */}
      <dl className="grid gap-x-8 gap-y-3 text-base text-ink md:grid-cols-2">
        {org.local_script.value ? (
          <div className="flex min-h-11 flex-wrap items-center gap-2 md:col-span-2">
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

        {org.legal_name.value && org.legal_name.value !== org.name ? (
          <div className="flex min-h-11 flex-wrap items-center gap-x-2 gap-y-1 md:col-span-2">
            <dt className="text-sm text-muted">{t("legalNameLabel")}</dt>
            <dd>
              <Datum
                datum={org.legal_name}
                field={t("legalNameLabel")}
                variant="inline"
                id="legal-name"
              />
            </dd>
          </div>
        ) : null}

        {org.aliases.length > 0 ? (
          <div className="md:col-span-2">
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
