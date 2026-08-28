import type { Datum, DatumState } from "@/lib/types";
import { gapLabelKey } from "./state";
import type { MarkKey } from "./marks";

/**
 * Three tones, and none of them is a traffic light.
 *
 * "doc"  a document backs this: a register entry or an audited account
 * "ink"  someone said it: the organisation itself, or a third party
 * "open" the question is open: unverified, not found, unreachable, not published, old
 *
 * "open" is not a penalty. Its contrast is tuned to sit within 0.1 of "doc" precisely so
 * that a missing value does not read as weaker than a present one; scripts/contrast.mjs
 * fails the build if that ever drifts.
 */
export type Tone = "doc" | "ink" | "open";

export interface Vocabulary {
  mark: MarkKey;
  /** Key under common.datum.word */
  labelKey: string;
  /** Key under common.datum.sentence */
  sentenceKey: string;
  tone: Tone;
}

const TONE_CLASS: Record<Tone, string> = {
  doc: "text-mark-doc bg-mark-doc-tint",
  ink: "text-ink bg-transparent",
  open: "text-mark-open bg-mark-open-tint",
};

export function toneClass(tone: Tone): string {
  return TONE_CLASS[tone];
}

export function vocabularyFor(datum: Datum, state: DatumState): Vocabulary {
  switch (state) {
    case "value":
    case "stale": {
      const v = datum.verification;
      const tone: Tone =
        v === "register_confirmed" || v === "externally_audited" ? "doc" : "ink";
      return { mark: v as MarkKey, labelKey: v, sentenceKey: v, tone };
    }
    case "value_unverified":
      return {
        mark: "unverified",
        labelKey: "unverified",
        sentenceKey: "unverified",
        tone: "open",
      };
    case "source_unreachable":
      return {
        mark: "source_unreachable",
        labelKey: "source_unreachable",
        sentenceKey: "source_unreachable",
        tone: "open",
      };
    case "not_public":
      return { mark: "not_public", labelKey: "not_public", sentenceKey: "not_public", tone: "open" };
    case "not_found": {
      const key = gapLabelKey(datum);
      return { mark: key, labelKey: key, sentenceKey: key, tone: "open" };
    }
  }
}
