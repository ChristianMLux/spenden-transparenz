import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PageIntro } from "@/components/pages/page-intro";
import type { Locale } from "@/i18n/routing";
import { alternateLanguages, urlFor } from "@/lib/site";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.datenschutz" });
  return {
    title: t("title"),
    // Same reasoning as /impressum: the full text is Chris's to provide, not ours to
    // invent. Unindexed until it lands.
    robots: { index: false },
    alternates: { canonical: urlFor("/datenschutz", locale), languages: alternateLanguages("/datenschutz") },
  };
}

export default async function DatenschutzPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.datenschutz" });

  return (
    <article>
      <PageIntro title={t("title")} />
      <section className="max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("placeholderHeading")}</h2>
        <p>{t("placeholderBody")}</p>
      </section>
      <section className="mt-8 max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("factsHeading")}</h2>
        <p>{t("factsBody")}</p>
      </section>
    </article>
  );
}
