import { useTranslations } from "next-intl";

/** First focusable element on every page. Invisible until it is focused. */
export function SkipLink() {
  const t = useTranslations("common");
  return (
    <a
      href="#inhalt"
      className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:border focus:border-rule focus:bg-surface focus:px-3 focus:py-2 focus:text-sm"
    >
      {t("skipLink")}
    </a>
  );
}
