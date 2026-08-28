"use client";

import { useSyncExternalStore } from "react";

// Reading the path from the browser rather than from a router hook, for two reasons.
//
// First, a router hook is a dynamic API. Wrapping one in try/catch, which is what a
// localised-pathname switcher tempts you into, swallows Next's prerender bailout signal
// and breaks the partial shell of /krise/[crisis] with no usable error message.
//
// Second, it is unnecessary. Swapping only the locale segment produces a valid URL in
// every case; where the target locale spells the rest of the path differently
// (/krise/... against /crisis/...), the proxy redirects to the canonical form. That costs
// one redirect on an action people take rarely, and it cannot throw.
//
// All labels arrive as props, so this component does not pull next-intl into the client
// bundle.
function subscribe(listener: () => void) {
  window.addEventListener("popstate", listener);
  return () => window.removeEventListener("popstate", listener);
}

function getSnapshot() {
  return window.location.pathname;
}

export function LocaleSwitch({
  current,
  locales,
  navLabel,
  labels,
}: {
  current: string;
  locales: readonly string[];
  navLabel: string;
  labels: Record<string, string>;
}) {
  // On the server, and until hydration, each link points at the locale root. Always
  // correct, just less specific.
  const pathname = useSyncExternalStore(subscribe, getSnapshot, () => `/${current}`);

  const stripped = locales.reduce(
    (acc, locale) => (acc.startsWith(`/${locale}/`) ? acc.slice(locale.length + 1) : acc),
    pathname,
  );
  const suffix = stripped === pathname ? "" : stripped;

  return (
    <nav aria-label={navLabel} className="flex items-center gap-3 text-sm">
      {locales.map((locale) => (
        <a
          key={locale}
          href={`/${locale}${suffix}`}
          hrefLang={locale}
          aria-current={locale === current ? "true" : undefined}
          className={
            locale === current
              ? "flex min-h-11 items-center text-ink no-underline"
              : "flex min-h-11 items-center underline"
          }
        >
          {labels[locale]}
        </a>
      ))}
    </nav>
  );
}
