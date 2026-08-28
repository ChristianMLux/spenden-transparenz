import { useTranslations } from "next-intl";
import { Mark, type MarkKey } from "@/components/datum/marks";
import { toneClass, type Tone } from "@/components/datum/vocabulary";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import type { DonationView } from "@/lib/donation";

/**
 * The donation-channel line: mark, label, host, date, all as one link (or one plain
 * span when there is nothing to link to), in the same 13px block style
 * components/board/provenance-line.tsx already uses for a statement's own source. It is
 * a second, deliberate copy of that shape rather than a reuse of ProvenanceLine, because
 * a DonationView is not a Datum<T> (no `value`, no `is_gap`) and reshaping it into one
 * just to satisfy a shared component's prop type would be the kind of silent
 * reinterpretation this product's own rule against inventing structure warns against.
 * components/datum/** itself is untouched; this only reads its exported Mark and
 * toneClass, exactly as provenance-line.tsx already does.
 *
 * Tone follows the same doc/ink/open mapping components/datum/vocabulary.ts uses for a
 * verification grade, so a self-reported donation page reads in the same ink as a
 * self-reported statement, and "kein offizieller Spendenweg gefunden" reads in the same
 * open tint as "nicht gefunden" everywhere else — never grey, never smaller, never a
 * button. Identical treatment for every organisation and the government fund: nothing
 * here reads as a recommendation.
 */
function toneFor(view: DonationView): Tone {
  if (view.state !== "found") return "open";
  const v = view.verificationKey;
  if (v === "unverified") return "open";
  return v === "register_confirmed" || v === "externally_audited" ? "doc" : "ink";
}

function markFor(view: DonationView): MarkKey {
  if (view.state === "not_found") return "not_found";
  if (view.state === "not_searched") return "not_searched";
  return view.verificationKey as MarkKey;
}

export function DonationLine({ view, locale }: { view: DonationView; locale: Locale }) {
  const t = useTranslations("common");
  const tone = toneFor(view);
  const mark = markFor(view);
  const word = t(`donation.${view.labelKey}`);
  const dateLabel = view.retrieved_at
    ? view.state === "not_found"
      ? t("datum.searchedOn", { date: formatDate(view.retrieved_at, locale) })
      : view.state === "found"
        ? formatDate(view.retrieved_at, locale)
        : null
    : null;
  const parts = [word, view.publisher, dateLabel].filter((p): p is string => Boolean(p));

  const line = (
    <>
      <Mark mark={mark} />
      <span>{parts.join(" · ")}</span>
    </>
  );

  if (view.href) {
    return (
      <a
        href={view.href}
        rel="noopener"
        className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs no-underline hover:underline ${toneClass(tone)}`}
      >
        {line}
      </a>
    );
  }

  return (
    <span className={`inline-flex min-h-6 items-center gap-1 px-1 py-0.5 text-xs ${toneClass(tone)}`}>
      {line}
    </span>
  );
}
