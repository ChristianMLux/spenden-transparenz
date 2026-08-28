import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { domainOf, formatDate } from "@/lib/format";
import { NOW } from "@/lib/now";
import type { Datum } from "@/lib/types";
import { Mark } from "@/components/datum/marks";
import { datumState } from "@/components/datum/state";
import { toneClass, vocabularyFor } from "@/components/datum/vocabulary";

/**
 * The board's provenance footer. This is deliberately NOT <Datum variant="block">: that
 * component's module also imports DatumTrigger (the inline variant's Radix Popover
 * chip), and a bundler cannot tree-shake away a "use client" component that a shared
 * module references, even from a branch this page never takes. Importing components/
 * datum/datum.tsx from anywhere in this route therefore ships the whole Popover chunk
 * (~50 KB gz measured) to a page that never opens a popover, which alone put the board
 * over its 150 KB First Load JS budget.
 *
 * This file consumes the same three lower-level, non-client pieces WP0 exports for
 * exactly this purpose (components/datum/state.ts, vocabulary.ts, marks.tsx) and
 * reproduces <Datum>'s own block-variant branch verbatim, so the board renders byte-for-
 * byte the same markup as the org page will, without paying for a control it does not
 * use. It never modifies components/datum/**; nothing here is a fork of the popover
 * logic, only of the already-static block layout.
 */
export function ProvenanceLine({
  datum,
  staleAfterDays,
}: {
  datum: Datum;
  staleAfterDays?: number;
}) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const state = datumState(datum, { now: NOW, staleAfterDays });
  const vocab = vocabularyFor(datum, state);
  const word = t(`datum.word.${vocab.labelKey}`);

  const staleMark =
    state === "stale" ? (
      <span
        className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClass("open")}`}
      >
        <Mark mark="stale" />
        <span>{t("datum.word.stale")}</span>
      </span>
    ) : null;

  const domain = domainOf(datum.source_url);
  const dateLabel = datum.retrieved_at
    ? datum.value === null
      ? t("datum.searchedOn", { date: formatDate(datum.retrieved_at, locale) })
      : formatDate(datum.retrieved_at, locale)
    : null;
  const parts = [word, domain, dateLabel].filter((p): p is string => Boolean(p));

  const line = (
    <>
      <Mark mark={vocab.mark} />
      <span>{parts.join(" · ")}</span>
    </>
  );

  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      {datum.source_url ? (
        <a
          href={datum.source_url}
          rel="noopener"
          className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs no-underline hover:underline ${toneClass(vocab.tone)}`}
        >
          {line}
        </a>
      ) : (
        <span
          className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClass(vocab.tone)}`}
        >
          {line}
        </span>
      )}
      {staleMark}
    </span>
  );
}
