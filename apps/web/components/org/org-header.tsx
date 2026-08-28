import { useLocale, useTranslations } from "next-intl";
import { Datum } from "@/components/datum/datum";
import type { Locale } from "@/i18n/routing";
import { domainOf, formatDate } from "@/lib/format";
import type { OrgDetail } from "@/lib/types";
import { SourceToggleButton } from "./source-toggle";

/**
 * Section 1, "Kopf", inverted on the chrome (Variant C): name, aliases, type, seat,
 * website and last-updated sit in a two-column meta grid directly on the navy band, the
 * same surface the masthead and figure strip use. No score, no badge row, no summary
 * line (brief, verbatim).
 *
 * The Devanagari name and the legal name are deliberately NOT in that navy band, even
 * though DESIGN.md's original wireframe groups them with the rest of the header: both
 * render through <Datum variant="inline">, which is owned by WP0 and hardcodes
 * `text-ink` (and, for a self-/third-party-reported grade, a tone class that is also
 * `text-ink`) for its value and evidence-chip text. Placing either on a dark navy
 * background would either be unreadable (light mode: near-black ink on navy) or clash
 * with the tinted evidence marks. Touching components/datum/** was out of scope, so both
 * rows render just below the chrome band instead, on the ordinary canvas where <Datum>'s
 * own contrast is the one DESIGN.md already verified.
 *
 * `legal_name` is shown when it says something the common name does not: 37 of the 44
 * records carry one, and it is the most useful single fact for a reader who wants to
 * look the organisation up in a register themselves.
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
  const hasLocalScript = Boolean(org.local_script.value);
  const hasLegalName = Boolean(org.legal_name.value && org.legal_name.value !== org.name);

  return (
    <section aria-labelledby="org-name" className="break-inside-avoid">
      <div className="chrome-bleed bg-chrome text-chrome-ink">
        <div className="mx-auto max-w-[80rem] px-4 py-6 sm:py-8">
          <div className="flex flex-wrap items-baseline justify-between gap-4">
            <h2 id="org-name" className="text-xl text-chrome-ink">
              {org.name}
            </h2>
            <SourceToggleButton
              showLabel={tCommon("sources.showAll")}
              hideLabel={tCommon("sources.hideAll")}
            />
          </div>

          <dl className="mt-6 grid gap-x-8 gap-y-3 text-base text-chrome-ink sm:grid-cols-2">
            {org.aliases.length > 0 ? (
              <div className="sm:col-span-2">
                <dt className="inline text-sm text-chrome-muted">{t("aliasesLabel")}: </dt>
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
                  <a href={org.website} rel="noopener" className="text-chrome-ink underline">
                    {websiteDomain ?? org.website}
                  </a>
                </dd>
              </div>
            ) : null}

            <div className="text-sm text-chrome-muted">
              <dd>{t("lastUpdated", { date: formatDate(org.last_updated, locale) })}</dd>
            </div>
          </dl>
        </div>
      </div>

      {(hasLocalScript || hasLegalName) && (
        <dl className="mt-4 flex flex-col gap-2 text-base text-ink">
          {hasLocalScript ? (
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

          {hasLegalName ? (
            <div className="flex min-h-11 flex-wrap items-center gap-x-2 gap-y-1">
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
        </dl>
      )}
    </section>
  );
}
