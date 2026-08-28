import type { MetadataRoute } from "next";
import { ACTIVE_CRISIS, routing } from "@/i18n/routing";
import { listOrgIds } from "@/lib/api";
import { alternateLanguages, urlFor } from "@/lib/site";

// The trust pages that are actually indexable. /impressum and /datenschutz carry
// `robots: { index: false }` (see their generateMetadata) until Chris's operator details
// land; listing a noindex page in the sitemap would tell search engines to index exactly
// what the page itself says not to, so they are deliberately left out here too.
const INDEXABLE_TRUST_PAGES = ["/methodik", "/quellen", "/korrekturen"] as const;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const orgIds = await listOrgIds();
  const entries: MetadataRoute.Sitemap = [];

  for (const locale of routing.locales) {
    entries.push({
      url: urlFor({ pathname: "/krise/[crisis]", params: { crisis: ACTIVE_CRISIS } }, locale),
      alternates: { languages: alternateLanguages({ pathname: "/krise/[crisis]", params: { crisis: ACTIVE_CRISIS } }) },
      changeFrequency: "hourly",
    });
  }

  for (const orgId of orgIds) {
    for (const locale of routing.locales) {
      entries.push({
        url: urlFor({ pathname: "/organisation/[orgId]", params: { orgId } }, locale),
        alternates: { languages: alternateLanguages({ pathname: "/organisation/[orgId]", params: { orgId } }) },
        changeFrequency: "daily",
      });
    }
  }

  for (const page of INDEXABLE_TRUST_PAGES) {
    for (const locale of routing.locales) {
      entries.push({
        url: urlFor(page, locale),
        alternates: { languages: alternateLanguages(page) },
        changeFrequency: "monthly",
      });
    }
  }

  return entries;
}
