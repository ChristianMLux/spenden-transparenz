import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { CorrectionsLink } from "@/components/org/corrections-link";
import { DonationSection } from "@/components/org/donation-section";
import { FinancialsSection } from "@/components/org/financials-section";
import { GapsSection } from "@/components/org/gaps-section";
import { OrgHeader } from "@/components/org/org-header";
import { PresenceSection } from "@/components/org/presence-section";
import { RegistrationsSection } from "@/components/org/registrations-section";
import { ResponseSection } from "@/components/org/response-section";
import { SourceVisibilityScope } from "@/components/org/source-toggle";
import { WarningsSection } from "@/components/org/warnings-section";
import { routing } from "@/i18n/routing";
import { getFreshness, getOrg, listOrgIds } from "@/lib/api";
import printScope from "./print.module.css";

export async function generateStaticParams() {
  const orgIds = await listOrgIds();
  return routing.locales.flatMap((locale) => orgIds.map((orgId) => ({ locale, orgId })));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; orgId: string }>;
}): Promise<Metadata> {
  const { orgId } = await params;
  const [org, t] = await Promise.all([
    getOrg(orgId).catch(() => null),
    getTranslations("org.meta"),
  ]);
  if (!org) return {};
  return {
    title: t("titleTemplate", { name: org.name }),
    // Says what the page holds and, just as importantly, what it does not: no rating.
    description: t("description", { name: org.name }),
  };
}

export default async function OrgDetailPage({
  params,
}: {
  params: Promise<{ orgId: string }>;
}) {
  const { orgId } = await params;
  const org = await getOrg(orgId).catch(() => null);
  if (!org) notFound();

  const freshness = await getFreshness();

  return (
    <SourceVisibilityScope className={printScope.printScope}>
      <OrgHeader org={org} />
      <DonationSection org={org} />
      <ResponseSection
        statements={org.statements}
        researchNotes={org.research_notes}
        generatedAt={freshness.retrieved_at}
      />
      <PresenceSection org={org} />
      <RegistrationsSection registrations={org.registrations} />
      <FinancialsSection financials={org.financials} />
      <WarningsSection warnings={org.warnings} />
      <GapsSection org={org} />
      <CorrectionsLink orgId={org.org_id} />
    </SourceVisibilityScope>
  );
}
