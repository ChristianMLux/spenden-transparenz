"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

/**
 * "Alle Quellen anzeigen" (DESIGN.md 7.8, 8.3). Every `<Datum variant="inline">` already
 * renders its provenance body into the DOM at all times, hidden on screen by the global
 * `[data-expanded="true"] .datum-expanded` rule in globals.css and always shown under
 * `@media print`. This component only supplies the on-screen switch: it wraps the eight
 * sections in one element carrying `data-expanded`, so a single click anywhere in the
 * header reveals every source on the page at once.
 *
 * The print path never depends on this component: `@media print` in globals.css shows
 * `.datum-expanded` unconditionally, so a journalist who presses Ctrl+P without touching
 * this switch still gets full sources (verified in e2e/print.spec.ts).
 *
 * State also mirrors into `?quellen=alle` via history.replaceState so the expanded view
 * is a shareable link, per DESIGN.md 7.8. It intentionally does not read searchParams on
 * the server: this stays a plain static page, and the URL sync is a client-only
 * enhancement that degrades to "closed" if JavaScript never runs.
 */
const SourceVisibilityContext = createContext<{ expanded: boolean; toggle: () => void } | null>(
  null,
);

const PARAM = "quellen";
const PARAM_VALUE = "alle";

// Read once, at mount, whether this URL already asked for the expanded view (someone
// followed a shared "?quellen=alle" link). A lazy useState initialiser rather than an
// effect: this is a one-time derivation of the component's own initial value, not a
// subscription to an external system, so it belongs in render, not in a
// setState-inside-an-effect that eslint-plugin-react-hooks (rightly) flags as a
// cascading-render risk. On the server there is no window, so SSR output always starts
// collapsed; a visitor arriving via such a link sees one client-side correction, the
// same trade-off the "Alle Quellen anzeigen" switch already accepts everywhere else on
// this fully static page.
function initialExpanded(): boolean {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get(PARAM) === PARAM_VALUE;
}

export function SourceVisibilityScope({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const [expanded, setExpanded] = useState(initialExpanded);

  const toggle = () => {
    setExpanded((prev) => {
      const next = !prev;
      const url = new URL(window.location.href);
      if (next) url.searchParams.set(PARAM, PARAM_VALUE);
      else url.searchParams.delete(PARAM);
      window.history.replaceState(null, "", url);
      return next;
    });
  };

  return (
    <SourceVisibilityContext.Provider value={{ expanded, toggle }}>
      <div className={className} data-expanded={expanded ? "true" : undefined}>
        {children}
      </div>
    </SourceVisibilityContext.Provider>
  );
}

export function SourceToggleButton({
  showLabel,
  hideLabel,
}: {
  showLabel: string;
  hideLabel: string;
}) {
  const ctx = useContext(SourceVisibilityContext);
  if (!ctx) return null;
  return (
    <button
      type="button"
      onClick={ctx.toggle}
      aria-pressed={ctx.expanded}
      className="min-h-11 border border-rule px-3 text-sm text-ink underline-offset-2 hover:underline print:hidden"
    >
      {ctx.expanded ? hideLabel : showLabel}
    </button>
  );
}
