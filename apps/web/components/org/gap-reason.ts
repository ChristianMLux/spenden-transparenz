import type { GapReason, OrgDetail } from "@/lib/types";

/**
 * "Was wir nicht wissen" groups plain path strings (`data_gaps`) by gap_reason, but
 * `data_gaps` itself carries no reason, only a dotted path or a free sentence. The
 * reason lives on the structured Datum at that path, so most entries are resolved by
 * reading it back from `org`. A handful of pilot-data entries are free prose that does
 * not map onto a known field (e.g. "current_response entries lack precise
 * district-level location detail"); those fall back to a text heuristic and, failing
 * that, to `searched_not_found`, the measured majority case (DESIGN.md 8.3).
 */
export function resolveGapReason(path: string, org: OrgDetail): GapReason {
  const known = knownFieldReason(path, org);
  if (known) return known;

  const bracket = /^registrations\[([^\]]+)\]\.identifier$/.exec(path);
  if (bracket) {
    const registration = org.registrations.find((r) => r.registry === bracket[1]);
    if (registration?.datum.gap_reason) return registration.datum.gap_reason;
  }

  return textHeuristic(path);
}

function knownFieldReason(path: string, org: OrgDetail): GapReason | null {
  switch (path) {
    case "names.legal":
      return org.legal_name.gap_reason;
    case "names.local_script":
      return org.local_script.gap_reason;
    case "nepal_presence.since_year":
      return org.presence.since_year.gap_reason;
    case "nepal_presence.mode":
      return org.presence.mode.gap_reason;
    case "nepal_presence.staff_count":
      return org.presence.staff_count.gap_reason;
    case "financial_transparency.annual_report":
      return org.financials.annual_report.gap_reason;
    case "financial_transparency.audited_financials":
      return org.financials.audited.gap_reason;
    case "financial_transparency.iati_publisher":
      return org.financials.iati_ref.gap_reason;
    case "financial_transparency.income":
      return org.financials.income.gap_reason;
    case "financial_transparency.expenditure":
      return org.financials.expenditure.gap_reason;
    case "financial_transparency.program_ratio":
      return org.financials.program_ratio.gap_reason;
    default:
      return null;
  }
}

// Same spirit as lib/api.ts's gapReasonOf, applied to a gap's own path or note text
// instead of a research note. Kept as an independent, small function here rather than
// imported: lib/api.ts does not export it, and it belongs to WP0/WP3.
function textHeuristic(path: string): GapReason {
  if (/unreachable|not reachable|nicht erreichbar/i.test(path)) return "source_unreachable";
  if (/not published|does not publish|nicht ver(oe|ö)ffentlicht|not public/i.test(path)) {
    return "not_public";
  }
  return "searched_not_found";
}

export type GapGroups = Record<GapReason, string[]>;

const REASONS: readonly GapReason[] = [
  "searched_not_found",
  "not_searched",
  "source_unreachable",
  "not_public",
];

export function groupDataGaps(paths: string[], org: OrgDetail): GapGroups {
  const groups: GapGroups = {
    searched_not_found: [],
    not_searched: [],
    source_unreachable: [],
    not_public: [],
  };
  for (const path of paths) {
    const reason = resolveGapReason(path, org);
    groups[reason].push(path);
  }
  return groups;
}

export const GAP_REASON_ORDER = REASONS;
