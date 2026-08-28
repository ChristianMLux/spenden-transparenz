import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // /dev is the internal state-matrix route (see app/[locale]/dev/datum), never
      // meant for a reader. /api is the revalidate route handler: a secret-gated POST
      // endpoint, not a page, with nothing a crawler should fetch.
      disallow: ["/dev", "/api"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
