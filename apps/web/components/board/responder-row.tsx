import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { Amount } from "@/components/datum/amount";
import { DonationLine } from "@/components/donation/donation-line";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import { donationView } from "@/lib/donation";
import type { Responder, Statement } from "@/lib/types";
import { ProvenanceLine } from "./provenance-line";

/** ISO 3166-1 region names from the platform, not a hand-maintained table. */
function countryName(code: string, locale: Locale): string {
  try {
    return new Intl.DisplayNames([locale], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

/**
 * One line of the Organisation | Reaktion | Ort | Quelle und Stand | Spenden grid
 * (DESIGN.md-style table-like row, Variant C). first controls whether the leftmost cell
 * carries the
 * organisation's name, or stays an empty spacer: a multi-statement organisation only
 * names itself once, in the first line, exactly the way a spreadsheet leaves a repeated
 * group cell blank rather than rowspanning it. The empty spacer is skipped entirely on
 * mobile, where the grid collapses to one column and nothing needs to hold the slot.
 */
function OrgCell({
  first,
  headingId,
  responder,
  locale,
  tCommon,
}: {
  first: boolean;
  headingId: string;
  responder: Responder;
  locale: Locale;
  tCommon: ReturnType<typeof useTranslations>;
}) {
  if (!first) return <div aria-hidden="true" className="hidden min-w-0 md:block" />;
  return (
    <div className="min-w-0 py-3 md:py-2">
      <h2 id={headingId} className="text-lg">
        {responder.name}
      </h2>
      <p className="mt-0.5 text-xs text-muted">
        {countryName(responder.hq_country, locale)} · {tCommon(`orgType.${responder.org_type}`)}
      </p>
      {responder.aliases.length > 0 && (
        <p className="text-xs text-muted">{responder.aliases.join(" · ")}</p>
      )}
    </div>
  );
}

function ReaktionCell({ statement, locale }: { statement: Statement; locale: Locale }) {
  const hasAmount =
    statement.amount !== null && statement.currency !== null && statement.amount_basis !== null;
  return (
    <div className="min-w-0 flex flex-col justify-center gap-1 py-2 md:py-1">
      <p className="text-sm text-ink">{statement.datum.value}</p>
      {hasAmount && (
        <p className="text-xs text-muted">
          <Amount
            amount={statement.amount as number}
            currency={statement.currency as string}
            basis={statement.amount_basis!}
            locale={locale}
          />
        </p>
      )}
    </div>
  );
}

function OrtCell({ statement, tCommon }: { statement: Statement; tCommon: ReturnType<typeof useTranslations> }) {
  const districtLabel =
    statement.districts.length > 0
      ? statement.districts.map((d) => d.name).join(", ")
      : tCommon("district.none");
  return (
    <div className="min-w-0 flex items-center py-1 md:py-1">
      <span className="text-sm text-ink">{districtLabel}</span>
    </div>
  );
}

function QuelleCell({ statement, locale }: { statement: Statement; locale: Locale }) {
  const dateLabel = statement.happened_on ? formatDate(statement.happened_on, locale) : null;
  return (
    <div className="min-w-0 flex flex-col justify-center gap-1 py-2 md:py-1">
      {dateLabel && (
        <time dateTime={statement.happened_on ?? undefined} className="text-xs text-muted">
          {dateLabel}
        </time>
      )}
      <ProvenanceLine datum={statement.datum} />
    </div>
  );
}

/**
 * The action-path column: the official donation channel, org-level rather than
 * per-statement, so (like OrgCell) it only renders on the row's first line and stays an
 * empty spacer after it. Identical component, identical tone rules, for every
 * organisation and (in the help section, not here) the government fund: nothing about
 * this cell may read as a recommendation.
 */
function DonationCell({ first, donation, locale }: { first: boolean; donation: Responder["donation"]; locale: Locale }) {
  if (!first) return <div aria-hidden="true" className="hidden min-w-0 md:block" />;
  return (
    <div className="min-w-0 flex items-center py-1 md:py-1">
      <DonationLine view={donationView(donation)} locale={locale} />
    </div>
  );
}

/**
 * One row of Tab A, restyled as a table-like grid: Organisation | Reaktion | Ort |
 * Quelle und Stand. Server-rendered for the same reason the old Statement piece was:
 * <Datum>/ProvenanceLine read next-intl through hooks, which only works on the server in
 * this app.
 *
 * The rule that drives this file: an organisation with no statement gets the identical
 * <article> frame, the same heading size and the same vertical presence as one with
 * three. There is no branch here that changes the wrapper, only the content inside it,
 * and the empty case's sentence sits in the same Reaktion-column position and at the
 * same 15px weight a found statement's text uses.
 */
export function ResponderRow({ responder, generatedAt }: { responder: Responder; generatedAt: string }) {
  const t = useTranslations("board");
  const tCommon = useTranslations("common");
  const locale = useLocale() as Locale;
  const headingId = `org-${(responder.org_id ?? responder.org_name_raw).replace(/[^a-zA-Z0-9_-]/g, "-")}`;

  return (
    <article aria-labelledby={headingId}>
      {responder.statements.length > 0 ? (
        responder.statements.map((statement, i) => (
          <div key={statement.id} className="board-row-grid board-row-line px-2 md:items-center">
            <OrgCell
              first={i === 0}
              headingId={headingId}
              responder={responder}
              locale={locale}
              tCommon={tCommon}
            />
            <ReaktionCell statement={statement} locale={locale} />
            <OrtCell statement={statement} tCommon={tCommon} />
            <QuelleCell statement={statement} locale={locale} />
            <DonationCell first={i === 0} donation={responder.donation} locale={locale} />
          </div>
        ))
      ) : (
        <div className="board-row-grid board-row-line px-2 md:items-center">
          <OrgCell first headingId={headingId} responder={responder} locale={locale} tCommon={tCommon} />
          <div className="min-w-0 flex flex-col justify-center gap-1 py-2 md:col-span-3 md:py-1">
            <p className="text-sm text-ink">
              {t("empty.heading", { date: formatDate(generatedAt.slice(0, 10), locale) })}
            </p>
            <p className="text-xs text-muted">
              {t("empty.searchedLabel")} {t("empty.searchedText")}
            </p>
          </div>
          <DonationCell first donation={responder.donation} locale={locale} />
        </div>
      )}

      {responder.org_id && (
        <p className="px-2 py-2">
          {/* next/link's Link, not @/i18n/navigation's wrapped one: SiteFooter (every
              page's layout) already pays for Link's own runtime and for next-intl's
              pathname-translation chunk, so reusing plain next/link here with a
              manually built, locale-invariant href (the org route is identical in both
              locales, see routing.ts) adds nothing beyond what the shell already ships,
              while a raw <a> would have given up prefetching for no bundle benefit. */}
          <Link
            href={`/${locale}/organisation/${responder.org_id}`}
            className="text-sm text-accent underline-offset-2 hover:underline"
          >
            {t("viewOrg")}
          </Link>
        </p>
      )}
    </article>
  );
}
