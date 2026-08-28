import { useLocale, useTranslations } from "next-intl";
import { Amount } from "@/components/datum/amount";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Statement as StatementType } from "@/lib/types";
import { ProvenanceLine } from "./provenance-line";

/**
 * Server-rendered on purpose: reading translations through hooks only works on the
 * server in this app, because the root layout deliberately ships an EMPTY message
 * catalogue to the client (app/[locale]/layout.tsx). This component, and everything
 * under it, must therefore stay on the server; BoardExplorer (the client filter island)
 * only ever receives its finished output as a pre-rendered node and decides which of
 * these to show, never how to render one. See board-explorer.tsx.
 */
export function Statement({ statement }: { statement: StatementType }) {
  const tCommon = useTranslations("common");
  const locale = useLocale() as Locale;
  const hasAmount = statement.amount !== null && statement.currency !== null && statement.amount_basis !== null;
  const districtLabel =
    statement.districts.length > 0
      ? statement.districts.map((d) => d.name).join(", ")
      : tCommon("district.none");
  const dateLabel = statement.happened_on ? formatDate(statement.happened_on, locale) : null;

  return (
    <div>
      <p className="max-w-[68ch] text-base text-ink">{statement.datum.value}</p>
      <p className="mt-1 text-sm text-muted">
        {hasAmount && (
          <>
            <Amount
              amount={statement.amount as number}
              currency={statement.currency as string}
              basis={statement.amount_basis!}
              locale={locale}
            />
            {" · "}
          </>
        )}
        <span>{districtLabel}</span>
        {dateLabel && (
          <>
            {" · "}
            <time dateTime={statement.happened_on ?? undefined}>{dateLabel}</time>
          </>
        )}
      </p>
      <p className="mt-1">
        <ProvenanceLine datum={statement.datum} />
      </p>
    </div>
  );
}
