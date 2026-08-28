import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { BoardExplorer } from "@/components/board/board-explorer";
import type { BoardLabels } from "@/components/board/board-labels";
import { buildChronoNodes, buildDayLabels } from "@/components/board/chronological";
import { ResponderRow } from "@/components/board/responder-row";
import type { Locale } from "@/i18n/routing";
import { ACTIVE_CRISIS, routing } from "@/i18n/routing";
import { getBoard } from "@/lib/api";
import type { Responder } from "@/lib/types";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale, crisis: ACTIVE_CRISIS }));
}

// No `export const dynamicParams = false` here: Next 16 rejects that route segment
// config outright once cacheComponents is on ("Route segment config 'dynamicParams' is
// not compatible with nextConfig.cacheComponents"). generateStaticParams above lists
// the one crisis this version ships; getBoard() throws for anything else and Next
// renders the nearest not-found boundary for it.
export async function generateMetadata(): Promise<Metadata> {
  const locale = (await getLocale()) as Locale;
  const board = await getBoard(ACTIVE_CRISIS);
  return { title: locale === "de" ? board.crisis.name_de : board.crisis.name_en };
}

function formatDataStand(iso: string, locale: Locale): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(d);
}

const rowKey = (r: Responder) => r.org_id ?? r.org_name_raw;

export default async function BoardPage() {
  const locale = (await getLocale()) as Locale;
  const board = await getBoard(ACTIVE_CRISIS);
  const [t, tCommon] = await Promise.all([getTranslations("board"), getTranslations("common")]);

  // ---------------------------------------------------------------------
  // Plain-string labels for the client filter island. See board-labels.ts
  // for why this exists: the client message catalogue is deliberately empty.
  // ---------------------------------------------------------------------
  const optionLabel: Record<string, string> = {};
  const removeChipLabel: Record<string, string> = {};
  for (const f of board.facets.districts) {
    optionLabel[f.key] = f.key === "none" ? tCommon("district.none") : f.label_key;
  }
  for (const f of [...board.facets.hq, ...board.facets.orgType, ...board.facets.verification]) {
    optionLabel[f.key] = tCommon(f.label_key);
  }
  for (const key of Object.keys(optionLabel)) {
    removeChipLabel[key] = t("filters.removeChip", { label: optionLabel[key] ?? key });
  }

  const resultCountOrgs = Array.from({ length: board.counts.orgs + 1 }, (_, i) =>
    t("resultCount", { count: i, total: board.counts.orgs }),
  );
  const resultCountStatements = Array.from({ length: board.counts.statements + 1 }, (_, i) =>
    t("resultCountStatements", { count: i, total: board.counts.statements }),
  );
  const mobileOpenLabels = Array.from({ length: 30 }, (_, i) => t("filters.mobileOpen", { count: i }));

  const labels: BoardLabels = {
    numberLine: {
      orgs: t("numbers.orgs", { count: board.counts.orgs }),
      statements: t("numbers.statements", { count: board.counts.statements }),
      districts: t("numbers.districts", { count: board.counts.districts }),
      noResponse: t("numbers.noResponse", { count: board.counts.orgsWithoutResponse }),
    },
    dataStand: t("dataStand", { date: formatDataStand(board.generated_at, locale) }),
    sourcesLink: t("sourcesLink"),
    // Read directly from routing.pathnames (already-known, locale-keyed strings) rather
    // than calling next-intl's getPathname(): computed here, server-side, so nothing
    // about it needs to be re-verified against a client-side API this session could not
    // check against current docs (context7 was unavailable). See board-labels.ts.
    sourcesHref: `/${locale}${routing.pathnames["/quellen"][locale]}`,
    tabs: { orgs: t("tabs.orgs"), chronological: t("tabs.chronological") },
    resultCountOrgs,
    resultCountStatements,
    filters: {
      hint: t("filters.hint"),
      districtLegend: t("filters.district.legend"),
      hqLegend: t("filters.hq.legend"),
      orgTypeLegend: t("filters.orgType.legend"),
      verificationLegend: t("filters.verification.legend"),
      searchLegend: t("filters.search.legend"),
      searchLabel: t("filters.search.label"),
      sortLabel: t("filters.sort.label"),
      sortLatest: t("filters.sort.latest"),
      sortName: t("filters.sort.name"),
      sortFewestData: t("filters.sort.fewestData"),
      selectedHeading: t("filters.selectedHeading"),
      clearAll: t("filters.clearAll"),
      mobileOpenLabels,
      mobileClose: t("filters.mobileClose"),
      mobileTitle: t("filters.mobileTitle"),
      searchChipPrefix: t("filters.search.chipPrefix"),
      removeSearchLabel: t("filters.removeSearch"),
    },
    optionLabel,
    removeChipLabel,
    locatorCaption: t("locator.caption"),
  };

  // ---------------------------------------------------------------------
  // Every responder and every statement, pre-rendered once, server-side, so <Datum>
  // (which reads next-intl through hooks) never has to run in the client bundle. See
  // components/board/statement.tsx and board-explorer.tsx.
  // ---------------------------------------------------------------------
  const rowNodes: Record<string, ReactNode> = {};
  for (const r of board.responders) {
    rowNodes[rowKey(r)] = <ResponderRow key={rowKey(r)} responder={r} generatedAt={board.generated_at} />;
  }
  const chronoNodes = buildChronoNodes(board.responders);
  const dayLabels = buildDayLabels(board.responders, locale, t("chronological.noDate"));

  const crisisName = locale === "de" ? board.crisis.name_de : board.crisis.name_en;

  return (
    <div>
      <h1 className="text-2xl">{crisisName}</h1>
      <p className="mt-1 font-mono text-xs text-muted">{board.crisis.glide_id}</p>

      <p className="mt-4 max-w-[68ch] text-base text-ink">
        {t("scopeLine1")} {t("scopeLine2")}
      </p>

      <div className="mt-6">
        <BoardExplorer
          board={board}
          rowNodes={rowNodes}
          chronoNodes={chronoNodes}
          dayLabels={dayLabels}
          labels={labels}
        />
      </div>
    </div>
  );
}
