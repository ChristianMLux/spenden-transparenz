import { relativeDays } from "@/lib/format";
import type { Datum, DatumState, GapReason } from "@/lib/types";

export const DEFAULT_STALE_AFTER_DAYS = 30;

export interface DatumStateOptions {
  /** Passed in, never Date.now(). Static output must be reproducible. */
  now: Date;
  staleAfterDays?: number;
}

/**
 * Six visual states. The four gap reasons collapse into three of them, because
 * "we did not search" and "we searched and found nothing" look identical and read
 * differently: same ink, same weight, different sentence. See gapLabelKey.
 *
 * `value` is the single source of truth for presence. `is_gap` is a convenience flag on
 * the wire and is deliberately not trusted here, so one inconsistent record cannot blank
 * out a value that actually exists.
 */
export function datumState(d: Datum, opts: DatumStateOptions): DatumState {
  if (d.value !== null) {
    if (d.verification === "unverified") return "value_unverified";
    if (d.retrieved_at) {
      const age = relativeDays(d.retrieved_at, opts.now);
      if (age > (opts.staleAfterDays ?? DEFAULT_STALE_AFTER_DAYS)) return "stale";
    }
    return "value";
  }

  switch (d.gap_reason) {
    case "source_unreachable":
      return "source_unreachable";
    case "not_public":
      return "not_public";
    default:
      return "not_found";
  }
}

/**
 * Which word the not_found state shows. Claiming to have searched where we did not is
 * exactly the kind of small dishonesty this product cannot afford.
 */
export function gapLabelKey(d: Datum): "not_found" | "not_searched" {
  const reason: GapReason | null = d.gap_reason;
  return reason === "not_searched" ? "not_searched" : "not_found";
}
