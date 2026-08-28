import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { BoardExplorer } from "@/components/board/board-explorer";
import type { BoardLabels } from "@/components/board/board-labels";
import { buildChronoNodes, buildDayLabels } from "@/components/board/chronological";
import { ResponderRow } from "@/components/board/responder-row";
import { DonationLine } from "@/components/donation/donation-line";
import type { Locale } from "@/i18n/routing";
import { ACTIVE_CRISIS, routing } from "@/i18n/routing";
import { getBoard } from "@/lib/api";
import { donationView } from "@/lib/donation";
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
  const t = await getTranslations("board");
  return {
    title: locale === "de" ? board.crisis.name_de : board.crisis.name_en,
    // The same two sentences the page opens with. A search result that promises a
    // ranking and delivers a register would be the first lie the product tells.
    description: `${t("scopeLine1")} ${t("scopeLine2")}`,
  };
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
      // Pre-formatted server-side for every count a group can hide, so the client
      // component never needs the message catalogue.
      moreLabels: Object.fromEntries(
        Array.from({ length: 12 }, (_, n) => [n, t("filters.more", { n })]),
      ),
      moreLabelFallback: t("filters.more", { n: 1 }),
      lessLabel: t("filters.less"),
    },
    optionLabel,
    removeChipLabel,
    districtsLabel: t("districtsLabel"),
    columns: {
      organisation: t("columns.organisation"),
      reaktion: t("columns.reaktion"),
      ort: t("columns.ort"),
      quelleUndStand: t("columns.quelleUndStand"),
      // Reused verbatim, not invented: the action path's copy is authored once for all
      // three variants, and a column header is still donation copy.
      spenden: tCommon("donation.label"),
    },
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

  // Server-rendered (next-intl only works through hooks on the server, see
  // board-explorer.tsx) and handed to the client island as a slot, so it can be placed
  // AFTER the chrome's figure strip in the DOM: the masthead and the figures are one
  // navy block, the crisis heading is the canvas's own first thing below it.
  //
  // The old scopeLine1/scopeLine2 paragraph is gone from here on purpose: help.line1
  // and help.line2 say almost the same thing, so this is a fold, not an addition. The
  // metadata description below still uses scopeLine1/2 (an OG description is not a
  // second on-page paragraph). "Ich möchte helfen" is a real landmark (#helfen), jumped
  // to from a link in the masthead in every locale, so it needs a heading of its own.
  const fundLines = board.government_funds.map((fund) => (
    <p key={fund.name} className="mt-1 max-w-[68ch] text-sm text-ink">
      <span className="text-muted">{t("help.governmentHeading")}: </span>
      <span className="font-semibold">{fund.name}</span>
      <span className="text-muted"> — {t("help.governmentNote")} </span>
      <DonationLine view={donationView(fund)} locale={locale} />
    </p>
  ));

  const intro = (
    <>
      <h1 className="text-2xl">{crisisName}</h1>
      <p className="mt-1 font-mono text-xs text-muted">{board.crisis.glide_id}</p>
      <section id="helfen" aria-labelledby="helfen-heading" className="mt-2">
        <h2 id="helfen-heading" className="text-lg">
          {t("help.heading")}
        </h2>
        <p className="mt-1 max-w-[68ch] text-sm text-ink">
          {t("help.line1")} {t("help.line2")} {t("help.line3")}
        </p>
        {fundLines}
      </section>
    </>
  );

  return (
    <div>
      <BoardExplorer
        board={board}
        rowNodes={rowNodes}
        chronoNodes={chronoNodes}
        dayLabels={dayLabels}
        labels={labels}
        intro={intro}
      />
    </div>
  );
}
