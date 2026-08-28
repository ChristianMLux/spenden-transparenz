import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";
import * as rootParams from "next/root-params";
import { routing } from "./routing";

// One namespace per work package. common is lead-owned; board, org and pages belong to
// WP1, WP2 and WP3 respectively, which is what keeps three workers out of one file.
const NAMESPACES = ["common", "board", "org", "pages"] as const;

export default getRequestConfig(async ({ locale }) => {
  if (!locale) {
    // next/root-params is available by default from Next 16.3. It replaces
    // setRequestLocale and keeps the app eligible for static rendering.
    const fromParams = await rootParams.locale();
    if (!hasLocale(routing.locales, fromParams)) notFound();
    locale = fromParams;
  }

  const loaded = await Promise.all(
    NAMESPACES.map((ns) => import(`../messages/${locale}/${ns}.json`).then((m) => m.default)),
  );

  return {
    locale,
    messages: Object.fromEntries(NAMESPACES.map((ns, i) => [ns, loaded[i]])),
    timeZone: "Europe/Berlin",
  };
});
