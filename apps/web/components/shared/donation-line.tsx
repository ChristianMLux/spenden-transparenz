import { useLocale, useTranslations } from "next-intl";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import { donationView } from "@/lib/donation";
import type { DonationChannel, DonationLink } from "@/lib/types";
import { Mark, type MarkKey } from "@/components/datum/marks";
import { toneClass, type Tone } from "@/components/datum/vocabulary";

/**
 * The official-donation-channel line, used everywhere one appears: the board row, the
 * organisation page, and the government fund entry in the "Ich möchte helfen" section.
 * One component means the "nicht gefunden" parity rule (BRIEF, action path, item b) can
 * only be true or false once, not once per place it is rendered.
 *
 * Deliberately not <Datum variant="inline">: that component always falls back to the
 * generic common.datum.word.* vocabulary for a null value ("nicht gefunden"), with no
 * way to substitute common.donation.notFound instead, and lib/donation.ts's whole point
 * is that this field's copy is a single tested function, not the general Datum
 * vocabulary. This reads Mark and toneClass from components/datum/* (the same read-only
 * reuse provenance-line.tsx already does for the board) and composes the rest itself.
 *
 * Same block treatment DESIGN.md already uses for every other source line: the whole
 * line is the link when there is one, the identical classes when there is not, so a
 * missing channel never reads as smaller, greyer or less certain than a found one.
 */
export function DonationLine({ channel }: { channel: DonationLink | DonationChannel }) {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const view = donationView(channel);

  const mark: MarkKey =
    view.state === "not_found" || view.state === "not_searched" ? view.state : (view.verificationKey as MarkKey);
  const tone: Tone =
    view.state !== "found"
      ? "open"
      : view.verificationKey === "register_confirmed" || view.verificationKey === "externally_audited"
        ? "doc"
        : "ink";

  const label = t(`donation.${view.labelKey}`);
  const dateLabel = view.retrieved_at ? formatDate(view.retrieved_at, locale) : null;
  const verificationWord = view.state === "found" ? t(`datum.word.${view.verificationKey}`) : null;
  const parts = [label, view.publisher, dateLabel, verificationWord].filter((p): p is string => Boolean(p));

  const line = (
    <>
      <Mark mark={mark} />
      <span>{parts.join(" · ")}</span>
    </>
  );

  return view.href ? (
    <a
      href={view.href}
      rel="noopener"
      className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs no-underline hover:underline ${toneClass(tone)}`}
    >
      {line}
    </a>
  ) : (
    <span className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClass(tone)}`}>{line}</span>
  );
}
