import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { DefinitionList } from "@/components/pages/definition-list";
import { PageIntro } from "@/components/pages/page-intro";
import type { Locale } from "@/i18n/routing";
import { alternateLanguages, urlFor } from "@/lib/site";
import type { GapReason, Verification } from "@/lib/types";

const GRADES: Verification[] = [
  "register_confirmed",
  "externally_audited",
  "self_reported",
  "third_party_reported",
  "unverified",
];

// gapLabelKey (components/datum/state.ts) collapses not_searched into its own label and
// every other gap reason into the label matching its own visual state, so the fourth row
// here reads "not_found" even though the underlying reason is searched_not_found.
const GAP_REASONS: { reason: GapReason; labelKey: "not_searched" | "not_found" | GapReason }[] = [
  { reason: "not_searched", labelKey: "not_searched" },
  { reason: "searched_not_found", labelKey: "not_found" },
  { reason: "source_unreachable", labelKey: "source_unreachable" },
  { reason: "not_public", labelKey: "not_public" },
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.methodik" });
  return {
    title: t("title"),
    description: t("intro"),
    alternates: { canonical: urlFor("/methodik", locale), languages: alternateLanguages("/methodik") },
  };
}

export default async function MethodikPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "pages.methodik" });
  const datum = await getTranslations({ locale, namespace: "common.datum" });

  const gradeItems = GRADES.map((grade) => ({
    term: datum(`word.${grade}`),
    definition: datum(`sentence.${grade}`),
  }));
  const reasonItems = GAP_REASONS.map(({ labelKey }) => ({
    term: datum(`word.${labelKey}`),
    definition: datum(`sentence.${labelKey}`),
  }));

  return (
    <article>
      <PageIntro title={t("title")} intro={t("intro")} />

      <section className="max-w-[68ch]">
        <h2 className="mb-3">{t("gradesHeading")}</h2>
        <p className="mb-4 text-sm text-muted">{t("gradesIntro")}</p>
      </section>
      <DefinitionList items={gradeItems} />

      <section className="mt-8 max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("notFoundHeading")}</h2>
        <p className="mb-3">{t("notFoundBody1")}</p>
        <p className="mb-3">{t("notFoundBody2")}</p>
        <p>{t("notFoundBody3")}</p>
      </section>

      <section className="mt-8 max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("reasonsHeading")}</h2>
        <p className="mb-4 text-sm text-muted">{t("reasonsIntro")}</p>
      </section>
      <DefinitionList items={reasonItems} />

      <section className="mt-8 max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("limitsHeading")}</h2>
        <p className="mb-3">{t("limitsBody1")}</p>
        <p className="mb-3">{t("limitsBody2")}</p>
        <p>{t("limitsBody3")}</p>
      </section>

      <section className="mt-8 max-w-[68ch] border-t border-rule pt-8">
        <h2 className="mb-3">{t("noRatingHeading")}</h2>
        <p>{t("noRatingBody")}</p>
      </section>
    </article>
  );
}
