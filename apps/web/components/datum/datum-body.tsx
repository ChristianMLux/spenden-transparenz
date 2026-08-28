import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { domainOf, formatDate, relativeDays } from "@/lib/format";
import { NOW } from "@/lib/now";
import type { Datum } from "@/lib/types";
import { datumState } from "./state";
import { vocabularyFor } from "./vocabulary";

/**
 * The provenance itself, in one fixed order, never varied per field:
 *
 *   1. the grade, as a sentence
 *   2. the retrieval date, absolute first and relative in brackets
 *   3. the quote, at most 40 words, marked as English
 *   4. the note
 *   5. the source, showing the domain a reader recognises, with the full URL beneath
 *
 * A block whose data is missing is left out entirely. No empty paragraph, and never the
 * string "null": the pilot data contains gaps whose note is genuinely absent.
 */
export function DatumBody({
  datum,
  field,
  headingId,
  staleAfterDays,
}: {
  datum: Datum;
  field: string;
  headingId: string;
  staleAfterDays?: number;
}) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const state = datumState(datum, { now: NOW, staleAfterDays });
  const vocab = vocabularyFor(datum, state);
  const domain = domainOf(datum.source_url);

  return (
    <div className="flex flex-col gap-2 text-sm">
      <p id={headingId} className="text-xs text-muted">
        {t("datum.heading", { field })}
      </p>

      <p className="text-ink">{t(`datum.sentence.${vocab.sentenceKey}`)}</p>

      {state === "stale" ? <p className="text-ink">{t("datum.sentence.stale")}</p> : null}

      {datum.retrieved_at ? (
        <p className="text-xs text-muted">
          {t("datum.retrievedOn", {
            date: formatDate(datum.retrieved_at, locale),
            // Clamped at zero: a retrieval date in the future is a data defect, and
            // "vor -2 Tagen" would be worse than reading it as today.
            relative: t("datum.daysAgo", {
              days: Math.max(0, relativeDays(datum.retrieved_at, NOW)),
            }),
          })}
        </p>
      ) : null}

      {datum.quote ? (
        <blockquote lang="en" className="border-l border-rule pl-2 text-ink">
          {datum.quote}
        </blockquote>
      ) : null}

      {datum.note ? <p className="text-xs text-muted">{datum.note}</p> : null}

      {datum.source_url && domain ? (
        <p className="flex flex-col gap-0.5">
          <a href={datum.source_url} rel="noopener" className="underline">
            {domain}
          </a>
          <span className="text-xs break-words text-muted [overflow-wrap:anywhere]">
            {datum.source_url}
          </span>
        </p>
      ) : null}
    </div>
  );
}
