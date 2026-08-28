import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { DonationView } from "@/lib/donation";
import { Mark, type MarkKey } from "@/components/datum/marks";
import { toneClass, type Tone } from "@/components/datum/vocabulary";

/**
 * Renders a DonationView (lib/donation.ts — the headless data layer shared by all three
 * WP4 variants) in this variant's own idiom: the same Mark-plus-tone-coloured chip every
 * other provenance line on this page already uses (ProvenanceLine, Datum's block
 * variant). Deliberately not <Datum>: a donation channel is not a Datum (no gap_reason,
 * no popover, no `is_gap`), and components/datum/** is Lead-owned. This file only
 * *consumes* the exported Mark and toneClass — it never edits that directory.
 *
 * Found and not-found share one expression and one class list; only the tag (<a> vs
 * <span>) and the text differ, the same rule that governs every other provenance line on
 * this site. "kein offizieller Spendenweg gefunden" / "nicht nach einem Spendenweg
 * gesucht" can never end up smaller, lighter or greyer than a found channel.
 */
export function DonationLine({ view }: { view: DonationView }) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;

  const found = view.state === "found";
  const tone: Tone = !found
    ? "open"
    : view.verificationKey === "register_confirmed" || view.verificationKey === "externally_audited"
      ? "doc"
      : "ink";
  const mark: MarkKey = found
    ? (view.verificationKey as MarkKey)
    : view.state === "not_searched"
      ? "not_searched"
      : "not_found";

  // Found: the link's own label, the host, the retrieval date, then the verification
  // word — exactly the four segments the brief asks for, in that order. Not found: just
  // the one honest sentence, nothing invented to fill the line.
  const parts = found
    ? [
        t("donation.label"),
        view.publisher,
        view.retrieved_at ? formatDate(view.retrieved_at, locale) : null,
        t(`datum.word.${view.verificationKey}`),
      ]
    : [t(`donation.${view.labelKey}`)];

  const line = (
    <>
      <Mark mark={mark} />
      <span>{parts.filter((p): p is string => Boolean(p)).join(" · ")}</span>
    </>
  );

  const base = "inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs";

  return found && view.href ? (
    <a href={view.href} rel="noopener" className={`${base} no-underline hover:underline ${toneClass(tone)}`}>
      {line}
    </a>
  ) : (
    <span className={`${base} ${toneClass(tone)}`}>{line}</span>
  );
}
