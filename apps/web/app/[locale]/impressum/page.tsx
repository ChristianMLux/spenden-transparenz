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
  const t = await getTranslations({ locale, namespace: "pages.impressum" });
  return {
    title: t("title"),
    // The operator details this page requires by law (Betreiber, Anschrift, Kontakt)
    // have not been provided yet. Shipping this page unindexed until they land is
    // deliberate: see the task brief, "no invented address, company name or contact".
    robots: { index: false },
    alternates: { canonical: urlFor("/impressum", locale), languages: alternateLanguages("/impressum") },
  };
}

export default async function ImpressumPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.impressum" });

  return (
    <article>
      <PageIntro title={t("title")} />
      <section className="max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("placeholderHeading")}</h2>
        <p>{t("placeholderBody")}</p>
      </section>
    </article>
  );
}
