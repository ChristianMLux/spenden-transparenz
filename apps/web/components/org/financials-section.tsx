import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { Amount } from "@/components/datum/amount";
import { Datum } from "@/components/datum/datum";
import type { OrgDetail } from "@/lib/types";
import { OrgSection } from "./section";

/**
 * Section 5, "Finanzielle Transparenz": the empty case is the designed case. When
 * neither income nor expenditure carries a figure, this renders one paragraph, not a
 * table, ending in the measured fact that 0 of the 14 Nepali organisations in the
 * dataset publish a public income figure. When a figure exists, currency, fiscal year
 * and scope are written out through `<Amount>`, and `program_ratio` appears only
 * together with the formula in its note. No bar, no ring, no percentage donut.
 */
export function FinancialsSection({ financials }: { financials: OrgDetail["financials"] }) {
  const t = useTranslations("org.financial");
  const locale = useLocale() as Locale;

  const hasFigures =
    (financials.income.value !== null || financials.expenditure.value !== null) &&
    Boolean(financials.currency);

  const scopeText = financials.scope ? t(`scope.${financials.scope}`) : null;

  // The annual report and the audited-accounts flag are facts about financial
  // transparency whether or not a figure was found: 13 of the 44 records publish a report
  // and 6 publish audited accounts. Rendering them only next to a figure would have
  // hidden every one of them, because almost none of those records also carries an income
  // number. They appear in both branches.
  const documents = (
    <dl className="flex flex-col gap-3">
      <div className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1">
        <dt className="w-full text-sm text-muted md:w-40 md:shrink-0">{t("annualReportField")}</dt>
        <dd>
          <Datum
            datum={financials.annual_report}
            field={t("annualReportField")}
            variant="inline"
            render={(url) => (
              <a href={url} rel="noopener" className="underline">
                {financials.fiscal_year
                  ? t("annualReportWithYear", { year: financials.fiscal_year })
                  : t("annualReportValue")}
              </a>
            )}
            id="financial-annual-report"
          />
        </dd>
      </div>

      <div className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1">
        <dt className="w-full text-sm text-muted md:w-40 md:shrink-0">{t("auditedField")}</dt>
        <dd>
          <Datum
            datum={financials.audited}
            field={t("auditedField")}
            variant="inline"
            render={() => t("auditedValue")}
            id="financial-audited"
          />
        </dd>
      </div>
    </dl>
  );

  return (
    <OrgSection headingId="financial-heading" heading={t("heading")}>
      {!hasFigures ? (
        <div className="flex flex-col gap-4">
          {/* The empty case is the designed case (DESIGN.md 1): a tinted callout with an
              accent left rule, not a card and with no shadow (BRIEF, "Amtsblatt"). */}
          <div className="max-w-[68ch] border-l-[3px] border-accent bg-tint p-4">
            <div className="flex flex-col gap-2">
              <p className="text-base text-ink">{t("emptyIntro")}</p>
              <p className="text-base text-ink">{t("emptySearched")}</p>
              <p className="text-base text-ink">{t("emptyNormal")}</p>
              <p className="text-sm">
                <Link href="/methodik" className="underline">
                  {t("methodikLink")}
                </Link>
              </p>
            </div>
          </div>
          {documents}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <dl className="flex flex-col gap-3">
            <div className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1">
              <dt className="w-full text-sm text-muted md:w-40 md:shrink-0">
                {t("incomeField")}
              </dt>
              <dd>
                <Datum
                  datum={financials.income}
                  field={t("incomeField")}
                  variant="inline"
                  render={(value) => (
                    <Amount
                      amount={value}
                      currency={financials.currency ?? ""}
                      basis="reported"
                      locale={locale}
                    />
                  )}
                  id="financial-income"
                />
              </dd>
            </div>

            <div className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1">
              <dt className="w-full text-sm text-muted md:w-40 md:shrink-0">
                {t("expenditureField")}
              </dt>
              <dd>
                <Datum
                  datum={financials.expenditure}
                  field={t("expenditureField")}
                  variant="inline"
                  render={(value) => (
                    <Amount
                      amount={value}
                      currency={financials.currency ?? ""}
                      basis="reported"
                      locale={locale}
                    />
                  )}
                  id="financial-expenditure"
                />
              </dd>
            </div>

            {financials.program_ratio.value !== null ? (
              <div className="flex flex-col gap-1">
                <dt className="text-sm text-muted">{t("programRatioField")}</dt>
                <dd className="flex flex-col gap-1">
                  <div className="flex min-h-11 flex-wrap items-center gap-2">
                    <Datum
                      datum={financials.program_ratio}
                      field={t("programRatioField")}
                      variant="inline"
                      render={(value) =>
                        t("programRatioValue", { percent: Math.round(value * 100) })
                      }
                      id="financial-program-ratio"
                    />
                  </div>
                  {financials.program_ratio.note ? (
                    <p className="text-sm text-muted">
                      {t("programRatioFormula", { note: financials.program_ratio.note })}
                    </p>
                  ) : null}
                </dd>
              </div>
            ) : null}
          </dl>

          <p className="text-sm text-muted">
            {financials.fiscal_year ? t("fiscalYearLabel", { year: financials.fiscal_year }) : null}
            {financials.fiscal_year && scopeText ? " · " : null}
            {scopeText ? t("scopeLabel", { scope: scopeText }) : null}
          </p>

          {documents}
        </div>
      )}
    </OrgSection>
  );
}
