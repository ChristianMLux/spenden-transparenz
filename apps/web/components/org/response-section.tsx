import { useLocale, useTranslations } from "next-intl";
import { Amount } from "@/components/datum/amount";
import { Datum } from "@/components/datum/datum";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Statement } from "@/lib/types";
import { OrgSection } from "./section";

/**
 * Section 2, "Reaktion auf die Flut": the same statement building blocks as the board,
 * chronological, one `<Datum variant="block">` per statement. The empty case states the
 * absence plus what was searched, from `research_notes`, with the same visual weight as
 * a filled section.
 */
export function ResponseSection({
  statements,
  researchNotes,
  generatedAt,
}: {
  statements: Statement[];
  researchNotes: string | null;
  generatedAt: string;
}) {
  const t = useTranslations("org.response");
  const locale = useLocale() as Locale;

  const sorted = [...statements].sort((a, b) => {
    if (a.happened_on && b.happened_on) return b.happened_on.localeCompare(a.happened_on);
    if (a.happened_on) return -1;
    if (b.happened_on) return 1;
    return 0;
  });

  return (
    <OrgSection headingId="response-heading" heading={t("heading")}>
      {sorted.length === 0 ? (
        <div className="flex flex-col gap-2">
          <p className="text-base text-ink">
            {t("empty", { date: formatDate(generatedAt.slice(0, 10), locale) })}
          </p>
          {researchNotes ? (
            <p className="text-sm text-ink">
              {t("searchedLabel")} {researchNotes}
            </p>
          ) : null}
        </div>
      ) : (
        <ul className="flex flex-col gap-4">
          {sorted.map((statement, index) => (
            <li
              key={statement.id}
              className={index === 0 ? "" : "border-t border-dashed border-rule pt-4"}
            >
              <p className="max-w-[68ch] text-base text-ink">{statement.datum.value}</p>
              {statement.amount !== null && statement.currency && statement.amount_basis ? (
                <p className="mt-1 text-sm">
                  <Amount
                    amount={statement.amount}
                    currency={statement.currency}
                    basis={statement.amount_basis}
                    locale={locale}
                  />
                </p>
              ) : null}
              <div className="mt-1">
                <Datum
                  datum={statement.datum}
                  field={t("field")}
                  variant="block"
                  id={`statement-${statement.id}`}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </OrgSection>
  );
}
