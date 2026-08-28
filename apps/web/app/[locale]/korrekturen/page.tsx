import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PageIntro } from "@/components/pages/page-intro";
import { type Column, ResponsiveTable } from "@/components/pages/responsive-table";
import type { Locale } from "@/i18n/routing";
import { getCorrections } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { alternateLanguages, urlFor } from "@/lib/site";
import type { Correction } from "@/lib/types";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.korrekturen" });
  return {
    title: t("title"),
    description: t("intro"),
    alternates: { canonical: urlFor("/korrekturen", locale), languages: alternateLanguages("/korrekturen") },
  };
}

export default async function KorrekturenPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.korrekturen" });
  const corrections = await getCorrections();

  const columns: Column<Correction & { key: string }>[] = [
    { key: "date", header: t("tableDate"), cell: (c) => formatDate(c.date, locale) },
    { key: "org", header: t("tableOrg"), cell: (c) => c.org_name },
    { key: "field", header: t("tableField"), cell: (c) => c.field },
    { key: "before", header: t("tableBefore"), cell: (c) => c.before },
    { key: "after", header: t("tableAfter"), cell: (c) => c.after },
    {
      key: "source",
      header: t("tableSource"),
      cell: (c) => (
        <a href={c.source_url} rel="noopener" className="underline">
          {t("sourceLinkLabel")}
        </a>
      ),
    },
  ];

  return (
    <article>
      <PageIntro title={t("title")} intro={t("intro")} />

      <ResponsiveTable
        columns={columns}
        rows={corrections.map((c, i) => ({ ...c, key: `${c.org_id}-${c.field}-${i}` }))}
      />
    </article>
  );
}
