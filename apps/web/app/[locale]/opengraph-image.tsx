import { ImageResponse } from "next/og";
import { getTranslations } from "next-intl/server";
import { ACTIVE_CRISIS, type Locale } from "@/i18n/routing";
import { getBoard } from "@/lib/api";
import { formatDate } from "@/lib/format";

// Deliberately under [locale], not at the app root: next-intl's proxy (middleware)
// redirects any extensionless path to add a locale prefix, including "/opengraph-image"
// (its matcher only excludes paths that already contain a dot), and a root-level file
// only answers at the un-prefixed path. The redirect landed on a 404 every time until
// this moved here, which is also correctly locale-aware now instead of German-only.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Spenden-Transparenz";

const INK = "#1A1A18";
const MUTED = "#4A4A46";
const BG = "#FCFCFA";
const RULE = "#E2E1DC";

export default async function OpengraphImage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const [board, t] = await Promise.all([getBoard(ACTIVE_CRISIS), getTranslations({ locale, namespace: "pages.og" })]);

  const name = locale === "de" ? board.crisis.name_de : board.crisis.name_en;
  const dataStand = formatDate(board.generated_at.slice(0, 10), locale);
  const countLine = [
    `${board.counts.orgs} ${t("orgsLabel")}`,
    `${board.counts.statements} ${t("statementsLabel")}`,
    `${board.counts.districts} ${t("districtsLabel")}`,
    `${board.counts.orgsWithoutResponse} ${t("noResponseLabel")}`,
  ].join(" · ");

  return new ImageResponse(
    (
      // Text only, in the light-theme tokens from app/globals.css: satori cannot resolve
      // this app's CSS custom properties, so the hex values are repeated here rather
      // than imported. No photo, no map, no illustration: the spec forbids images of the
      // disaster and does not carve out an exception for the share card.
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: 80,
          backgroundColor: BG,
          color: INK,
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", fontSize: 28, color: MUTED, marginBottom: 20 }}>{t("siteName")}</div>
        <div
          style={{
            display: "flex",
            fontSize: 56,
            fontWeight: 700,
            marginBottom: 36,
            maxWidth: 1000,
            lineHeight: 1.15,
          }}
        >
          {name}
        </div>
        <div style={{ display: "flex", width: 120, height: 2, backgroundColor: RULE, marginBottom: 36 }} />
        <div style={{ display: "flex", fontSize: 28, color: INK, marginBottom: 20, maxWidth: 1000 }}>
          {countLine}
        </div>
        <div style={{ display: "flex", fontSize: 22, color: MUTED }}>{t("dataStand", { date: dataStand })}</div>
      </div>
    ),
    { ...size },
  );
}
