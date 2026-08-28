import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PageIntro } from "@/components/pages/page-intro";
import { type Column, ResponsiveTable } from "@/components/pages/responsive-table";
import type { Locale } from "@/i18n/routing";
import { formatDate } from "@/lib/format";
import { getSources } from "@/lib/api";
import { alternateLanguages, urlFor } from "@/lib/site";
import type { SourceEntry } from "@/lib/types";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.quellen" });
  return {
    title: t("title"),
    description: t("intro"),
    alternates: { canonical: urlFor("/quellen", locale), languages: alternateLanguages("/quellen") },
  };
}

export default async function QuellenPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.quellen" });
  const sources = await getSources();

  const columns: Column<SourceEntry & { key: string }>[] = [
    { key: "name", header: t("tableName"), cell: (s) => s.name },
    { key: "licence", header: t("tableLicence"), cell: (s) => s.licence || t("licenceUnknown") },
    {
      key: "retrieved",
      header: t("tableRetrieved"),
      cell: (s) => (/^\d{4}-\d{2}-\d{2}/.test(s.retrieved_at) ? formatDate(s.retrieved_at.slice(0, 10), locale) : s.retrieved_at),
    },
    {
      key: "link",
      header: t("tableLink"),
      cell: (s) => (
        <a href={s.url} rel="noopener" className="underline">
          {new URL(s.url).hostname.replace(/^www\./, "")}
        </a>
      ),
    },
  ];

  return (
    <article>
      <PageIntro title={t("title")} intro={t("intro")} />

      <ResponsiveTable columns={columns} rows={sources.map((s) => ({ ...s, key: s.key }))} />

      <section className="mt-8 max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("downloadHeading")}</h2>
        <p className="mb-3">{t("downloadBody")}</p>
        <a href="/datasets/orgs-nepal-2026.json" className="min-h-11 inline-flex items-center underline">
          {t("downloadLink")}
        </a>
      </section>
    </article>
  );
}
