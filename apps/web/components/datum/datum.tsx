import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { Locale } from "@/i18n/routing";
import { domainOf, formatDate } from "@/lib/format";
import { NOW } from "@/lib/now";
import type { Datum as DatumType } from "@/lib/types";
import { DatumBody } from "./datum-body";
import { DatumTrigger } from "./datum-trigger";
import { Mark } from "./marks";
import { datumState } from "./state";
import { toneClass, vocabularyFor } from "./vocabulary";

export interface DatumProps<T> {
  datum: DatumType<T>;
  /** Already localised field name. Required: it is what makes the chip's name unique. */
  field: string;
  variant: "block" | "inline";
  /** How to print the value. Numbers go through <Amount>, never through here. */
  render?: (value: T) => ReactNode;
  staleAfterDays?: number;
  /** Stable id fragment so the popover heading can be referenced. */
  id: string;
}

/**
 * The one component that renders a provenance-carrying value.
 *
 * variant="block": the board. Provenance is always visible and the whole line is the
 * link. No popover, no client JavaScript.
 *
 * variant="inline": the organisation page. The value, then a chip that opens the
 * provenance in a popover.
 *
 * The rule that outranks everything else in this file: a found value and a missing one
 * are rendered by the same expression with the same classes, and only the text differs.
 * They cannot drift apart, because there is only one of them.
 */
export function Datum<T>({ datum, field, variant, render, staleAfterDays, id }: DatumProps<T>) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const state = datumState(datum, { now: NOW, staleAfterDays });
  const vocab = vocabularyFor(datum, state);
  const word = t(`datum.word.${vocab.labelKey}`);
  const headingId = `datum-${id}`;

  // A stale reading is a value plus a second statement, never a weakened value. It keeps
  // its own grade mark and gains one more; nothing about the value itself changes.
  const staleMark =
    state === "stale" ? (
      <span
        className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClass("open")}`}
      >
        <Mark mark="stale" />
        <span>{t("datum.word.stale")}</span>
      </span>
    ) : null;

  if (variant === "block") {
    const domain = domainOf(datum.source_url);
    const dateLabel = datum.retrieved_at
      ? datum.value === null
        ? // "searched on 28.08.2026" says what actually happened. A bare date next to
          // "not found" reads as if something had been found on that day.
          t("datum.searchedOn", { date: formatDate(datum.retrieved_at, locale) })
        : formatDate(datum.retrieved_at, locale)
      : null;
    const parts = [word, domain, dateLabel].filter((p): p is string => Boolean(p));

    const line = (
      <>
        <Mark mark={vocab.mark} />
        <span>{parts.join(" · ")}</span>
      </>
    );

    // With a source the whole line is the link. Without one it is the same line, at the
    // same size and weight, that simply does not lead anywhere.
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

  const shown =
    datum.value !== null && render
      ? render(datum.value)
      : datum.value !== null
        ? String(datum.value)
        : word;

  return (
    <span className="inline-flex min-h-11 flex-wrap items-center gap-2">
      {/* One expression, one class list. A value and a "nicht gefunden" are the same ink,
          the same size and the same weight; only the characters differ. */}
      <span className="text-base font-normal text-ink">{shown}</span>
      <DatumTrigger
        mark={vocab.mark}
        label={word}
        triggerLabel={t("datum.triggerLabel", { field, grade: word })}
        headingId={headingId}
        toneClassName={toneClass(vocab.tone)}
      >
        <DatumBody
          datum={datum}
          field={field}
          headingId={headingId}
          staleAfterDays={staleAfterDays}
        />
      </DatumTrigger>
      {staleMark}
      {/* Always in the DOM, hidden on screen unless expanded, always visible in print.
          Journalists press Ctrl+P without hunting for a toggle first. */}
      <span className="datum-expanded basis-full">
        <DatumBody
          datum={datum}
          field={field}
          headingId={`${headingId}-print`}
          staleAfterDays={staleAfterDays}
        />
      </span>
    </span>
  );
}
