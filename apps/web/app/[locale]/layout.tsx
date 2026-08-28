import type { Metadata } from "next";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { fontVariables } from "../fonts";
import { routing } from "@/i18n/routing";
import "../globals.css";

// This is the root layout. There is deliberately no app/layout.tsx above it: only a
// dynamic segment in the root layout becomes a root param, and next/root-params is what
// lets i18n/request.ts resolve the locale without setRequestLocale.
export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("common");
  return {
    title: { default: t("siteName"), template: `%s | ${t("siteName")}` },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();

  const messages = (await getMessages()) as Record<string, unknown>;

  return (
    <html lang={locale} className={fontVariables}>
      <body>
        {/* Only what client components actually read crosses the wire. Server
            components read every namespace directly. */}
        <NextIntlClientProvider messages={{ common: messages.common }}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
