import { useLocale, useTranslations } from "next-intl";
import type { CSSProperties } from "react";
import { Amount } from "@/components/datum/amount";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Statement as StatementType } from "@/lib/types";
import { ProvenanceLine } from "./provenance-line";

/**
 * One statement's three cells in the board's column grid (Reaktion | Ort | Quelle und
 * Stand), per BRIEF's variant-A column list. `row` sets the `--row` custom property
 * board-row's CSS (globals.css) reads to place these cells at md and up; below md the
 * three stack in plain document order as their own full-width blocks, which is also why
 * this is the only markup for a statement at either width — see responder-row.tsx and
 * the CSS for why one set of nodes serves both.
 *
 * A dashed rule marks the seam between stacked statements at every width. Server-
 * rendered on purpose: reading translations through hooks only works on the server in
 * this app, because the client message catalogue is deliberately empty (see
 * app/[locale]/layout.tsx). Statement text runs at 15px at md and up (DESIGN.md 5.4
 * reserves 15px for table cells specifically, and this is a real table-like grid there)
 * and at the 17px body size below it, where it is prose again, not a table cell.
 */
export function Statement({ statement, row, isFirst }: { statement: StatementType; row: number; isFirst: boolean }) {
  const tCommon = useTranslations("common");
  const locale = useLocale() as Locale;
  const hasAmount = statement.amount !== null && statement.currency !== null && statement.amount_basis !== null;
  const districtLabel =
    statement.districts.length > 0
      ? statement.districts.map((d) => d.name).join(", ")
      : tCommon("district.none");
  const dateLabel = statement.happened_on ? formatDate(statement.happened_on, locale) : null;

  const style = { "--row": row } as CSSProperties;
  // The dashed seam marks where statement N+1 begins. At md and up the three cells sit
  // side by side in one row, so all three need the rule for it to read as one
  // continuous line across the row. Stacked below md, the three are consecutive blocks
  // of the *same* statement; only the first (reaction) is where a new statement starts,
  // so only it carries the rule there, or "statement 2 starts here" would print three
  // times in a row instead of once.
  const seamReaction = isFirst ? "" : "border-t border-dashed border-rule pt-3";
  const seamRest = isFirst ? "" : "md:border-t md:border-dashed md:border-rule md:pt-3";

  return (
    <>
      <div style={style} className={`board-cell-reaction min-w-0 py-3 pr-2 md:min-h-16 ${seamReaction}`}>
        <p className="text-base text-ink md:text-sm">{statement.datum.value}</p>
        {hasAmount ? (
          <p className="mt-1 text-sm text-muted md:text-xs">
            <Amount
              amount={statement.amount as number}
              currency={statement.currency as string}
              basis={statement.amount_basis!}
              locale={locale}
            />
          </p>
        ) : null}
      </div>
      <div style={style} className={`board-cell-location min-w-0 py-3 pr-2 text-sm text-ink md:text-xs ${seamRest}`}>
        <p>{districtLabel}</p>
        {dateLabel ? (
          <p className="mt-1 text-muted">
            <time dateTime={statement.happened_on ?? undefined}>{dateLabel}</time>
          </p>
        ) : null}
      </div>
      <div style={style} className={`board-cell-source min-w-0 py-3 ${seamRest}`}>
        <ProvenanceLine datum={statement.datum} />
      </div>
    </>
  );
}
