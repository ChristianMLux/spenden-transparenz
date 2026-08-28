import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["de", "en"],
  defaultLocale: "de",
  localePrefix: "always",
  pathnames: {
    "/": "/",
    "/krise/[crisis]": { de: "/krise/[crisis]", en: "/crisis/[crisis]" },
    "/organisation/[orgId]": { de: "/organisation/[orgId]", en: "/organisation/[orgId]" },
    "/methodik": { de: "/methodik", en: "/methodology" },
    "/quellen": { de: "/quellen", en: "/sources" },
    "/korrekturen": { de: "/korrekturen", en: "/corrections" },
    "/impressum": { de: "/impressum", en: "/imprint" },
    "/datenschutz": { de: "/datenschutz", en: "/privacy" },
  },
});

export type Locale = (typeof routing.locales)[number];

// The one crisis this version covers. Kept here because the root redirect and the
// board both need it and neither owns it.
export const ACTIVE_CRISIS = "nepal-flut-2026";
