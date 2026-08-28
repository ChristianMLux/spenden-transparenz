import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import type { ReactNode } from "react";
import { Amount } from "@/components/datum/amount";
import type { Locale } from "@/i18n/routing";
import type { Responder, Statement as StatementType } from "@/lib/types";
import { ProvenanceLine } from "./provenance-line";

/**
 * One row of Tab B: the same statement content as Tab A, but naming its organisation as
 * a link instead of sitting inside that organisation's <article>. Server-rendered for
 * the same reason as components/board/statement.tsx: reading translations only works on
 * the server in this app.
 */
export function ChronoStatement({
  statement,
  org,
}: {
  statement: StatementType;
  org: Responder;
}) {
  const t = useTranslations("board");
  const locale = useLocale() as Locale;
  const hasAmount =
    statement.amount !== null && statement.currency !== null && statement.amount_basis !== null;

  // next/link's Link: see the note in responder-row.tsx. Permanently underlined, not
  // hover-only: "reported by {org}" puts this link inline in a sentence, and WCAG 1.4.1
  // needs more than colour to set it apart from the plain text next to it (axe:
  // link-in-text-block).
  const orgName = org.org_id ? (
    <Link
      href={`/${locale}/organisation/${org.org_id}`}
      className="text-accent underline underline-offset-2"
    >
      {org.name}
    </Link>
  ) : (
    <span>{org.name}</span>
  );

  return (
    <div>
      <p className="max-w-[68ch] text-base text-ink">{statement.datum.value}</p>
      <p className="mt-1 text-sm text-muted">
        {t("chronological.reportedBy")} {orgName}
        {hasAmount && (
          <>
            {" · "}
            <Amount
              amount={statement.amount as number}
              currency={statement.currency as string}
              basis={statement.amount_basis!}
              locale={locale}
            />
          </>
        )}
      </p>
      <p className="mt-1">
        <ProvenanceLine datum={statement.datum} />
      </p>
    </div>
  );
}

/** ISO date -> the fuller heading format ("28. August 2026"), distinct from the 13px
 * numeric meta-line format lib/format.ts owns, because this is an <h3>, not a footnote. */
export function formatDayHeading(iso: string, locale: Locale): string {
  const date = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export const UNDATED_KEY = "undated";

/** happened_on, falling back to when we retrieved the statement, so every row still
 * sorts and groups somewhere. Mirrors lib/filter.ts's own fallback for the "latest"
 * sort and flattenStatements, so the two never disagree about a statement's date. */
export function dayKeyOf(statement: StatementType): string {
  return statement.happened_on ?? statement.datum.retrieved_at ?? UNDATED_KEY;
}

/** Pre-renders every statement in the given responders once, keyed by statement id, so
 * the client filter island (board-explorer.tsx) can pick out the ones that remain after
 * filtering without ever rendering <Datum> itself. */
export function buildChronoNodes(responders: Responder[]): Record<string, ReactNode> {
  const nodes: Record<string, ReactNode> = {};
  for (const org of responders) {
    for (const statement of org.statements) {
      nodes[statement.id] = <ChronoStatement key={statement.id} statement={statement} org={org} />;
    }
  }
  return nodes;
}

/** Every distinct day key across all statements, pre-formatted, so the client only ever
 * looks a label up and never calls Intl.DateTimeFormat itself. */
export function buildDayLabels(responders: Responder[], locale: Locale, undatedLabel: string): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const org of responders) {
    for (const statement of org.statements) {
      const key = dayKeyOf(statement);
      if (!(key in labels)) {
        labels[key] = key === UNDATED_KEY ? undatedLabel : formatDayHeading(key, locale);
      }
    }
  }
  return labels;
}
