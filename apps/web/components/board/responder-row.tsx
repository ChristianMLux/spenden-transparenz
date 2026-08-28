import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import type { CSSProperties } from "react";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { Responder } from "@/lib/types";
import { Statement } from "./statement";

/** ISO 3166-1 region names from the platform, not a hand-maintained table. */
function countryName(code: string, locale: Locale): string {
  try {
    return new Intl.DisplayNames([locale], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

/**
 * One organisation's row. A single `.board-row` grid (globals.css) serves both
 * breakpoints: below md every cell auto-places into one column in document order (name,
 * then each statement's reaction/location/source, then the "view organisation" link),
 * which is a plain, honest stacked reading and needs no second copy of the same
 * content. At md and up the same cells carry `--row`/`--rows` custom properties that
 * the CSS reads to lay them into the real 4fr/5fr/2fr/3fr column grid (BRIEF,
 * "Amtsblatt": Organisation | Reaktion | Ort | Quelle und Stand), with the name cell
 * spanning every row its statements produced so the name is written once no matter how
 * many statements follow it. See statement.tsx and globals.css's `.board-row` block for
 * the mechanism.
 *
 * The "view organisation" link is its own cell, placed in document order *after* every
 * statement: e2e/board.spec.ts's keyboard-order test expects "filter, then a Datum
 * provenance link, then an organisation link" for the very first row on the page, which
 * only holds if this link is not the first focusable thing in the row.
 *
 * Server-rendered for the same reason as Statement: <Datum> and its lower-level pieces
 * need next-intl translations, which only exist on the server in this app.
 *
 * The rule that drives this file: an organisation with no statement gets the identical
 * frame, the same heading size and the same vertical presence as one with three. There
 * is no branch here that changes the wrapper, only the content inside it — the empty
 * case fills the reaction/location/source span with a full sentence, never a blank
 * cell, so it cannot collapse into a thin line.
 */
export function ResponderRow({ responder, generatedAt }: { responder: Responder; generatedAt: string }) {
  const t = useTranslations("board");
  const tCommon = useTranslations("common");
  const locale = useLocale() as Locale;
  const headingId = `org-${(responder.org_id ?? responder.org_name_raw).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const rowCount = Math.max(responder.statements.length, 1);
  const nameStyle = { "--rows": rowCount } as CSSProperties;
  const linkStyle = { "--row": rowCount + 1 } as CSSProperties;

  return (
    <article aria-labelledby={headingId} className="board-row border-b border-rule hover:bg-tint">
      <div style={nameStyle} className="board-cell-name min-w-0 self-start py-3 pr-2 md:min-h-16">
        <h2 id={headingId} className="text-lg">
          {responder.name}
        </h2>
        <p className="mt-1 text-sm text-muted md:text-xs">
          {tCommon(`orgType.${responder.org_type}`)} · {countryName(responder.hq_country, locale)}
        </p>
        {responder.aliases.length > 0 && (
          <p className="mt-1 text-sm text-muted md:text-xs">{responder.aliases.join(" · ")}</p>
        )}
      </div>

      {responder.statements.length > 0 ? (
        responder.statements.map((statement, i) => (
          <Statement key={statement.id} statement={statement} row={i + 1} isFirst={i === 0} />
        ))
      ) : (
        <div style={{ "--row": 1 } as CSSProperties} className="board-cell-empty min-w-0 py-3 md:min-h-16">
          <p className="max-w-[60ch] text-base text-ink md:text-sm">
            {t("empty.heading", { date: formatDate(generatedAt.slice(0, 10), locale) })}
          </p>
          <p className="mt-1 max-w-[60ch] text-sm text-ink md:text-xs">
            {t("empty.searchedLabel")} {t("empty.searchedText")}
          </p>
        </div>
      )}

      {responder.org_id && (
        <div style={linkStyle} className="board-cell-link pt-1 pb-3">
          {/* next/link's Link, not @/i18n/navigation's wrapped one: SiteFooter (every
              page's layout) already pays for Link's own runtime and for next-intl's
              pathname-translation chunk, so reusing plain next/link here with a
              manually built, locale-invariant href (the org route is identical in both
              locales, see routing.ts) adds nothing beyond what the shell already ships,
              while a raw <a> would have given up prefetching for no bundle benefit. */}
          <Link
            href={`/${locale}/organisation/${responder.org_id}`}
            className="text-sm text-accent underline-offset-2 hover:underline md:text-xs"
          >
            {t("viewOrg")}
          </Link>
        </div>
      )}
    </article>
  );
}
