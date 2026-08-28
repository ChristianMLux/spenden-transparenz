import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import { SiteFooter } from "@/components/shell/site-footer";
import { SiteHeader } from "@/components/shell/site-header";
import { SkipLink } from "@/components/shell/skip-link";
import { ThemeScript } from "@/components/shell/theme-script";
import { ACTIVE_CRISIS, routing } from "@/i18n/routing";
import { getCrisis, getFreshness } from "@/lib/api";
import { fontVariables } from "../fonts";
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

export default async function LocaleLayout({ children }: { children: React.ReactNode }) {
  // Not `await params`. Under cacheComponents that turns the layout dynamic and the
  // partial shell of /krise/[crisis] then fails to prerender. next-intl resolves the
  // locale through next/root-params, which is static-safe, and its request config
  // already calls notFound() for a locale that is not in the routing config.
  const locale = await getLocale();

  const t = await getTranslations("common");
  const [crisis, freshness] = await Promise.all([getCrisis(ACTIVE_CRISIS), getFreshness()]);

  return (
    <html lang={locale} className={fontVariables} suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className="flex min-h-screen flex-col">
        {/* The provider is present because next-intl needs it in the tree, but it
            carries no messages: every client component in this app takes its strings as
            props, so the catalogue never crosses the wire. */}
        <NextIntlClientProvider messages={{}}>
        <SkipLink />
        <SiteHeader crisis={crisis} siteName={t("siteName")} generatedAt={freshness.retrieved_at} />
        <main id="inhalt" tabIndex={-1} className="mx-auto w-full max-w-[80rem] flex-1 px-4 pt-4 pb-6">
          {children}
        </main>
        <SiteFooter generatedAt={freshness.retrieved_at} />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
