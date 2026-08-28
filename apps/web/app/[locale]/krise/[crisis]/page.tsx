import { ACTIVE_CRISIS, routing } from "@/i18n/routing";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale, crisis: ACTIVE_CRISIS }));
}

// Placeholder. WP1 owns this route.
export default function BoardPage() {
  return (
    <h1>Nepal</h1>
  );
}
