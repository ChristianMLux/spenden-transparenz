import { ACTIVE_CRISIS, routing } from "@/i18n/routing";
import { redirect } from "@/i18n/navigation";
import { hasLocale } from "next-intl";
import { notFound } from "next/navigation";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleIndex({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  redirect({
    href: { pathname: "/krise/[crisis]", params: { crisis: ACTIVE_CRISIS } },
    locale,
  });
}
