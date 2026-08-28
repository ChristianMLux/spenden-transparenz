import type { ReactNode } from "react";

/**
 * The one shared frame for the eight sections of the org page: a dossier panel (surface
 * one step lighter than the page, a 3px accent rule on its left edge, a 13px muted
 * label line above the heading — the device the whole variant is built on), 32px of
 * space above every panel but the first (DESIGN.md 5.5's spacing set), and
 * `break-inside-avoid` so a section never splits across a printed page. The first
 * section (the header) still gets the full panel treatment — it is "the first and
 * widest panel" per the variant brief — it only opts out of the top margin, since it
 * opens the page.
 */
export function OrgSection({
  headingId,
  heading,
  label,
  first = false,
  headingClassName = "text-lg",
  headingExtra,
  children,
}: {
  headingId: string;
  heading: ReactNode;
  /** The 13px muted label line above the heading, e.g. "Register" above "Registrierungen
   *  und Kennungen". Short, sentence case, new copy per section (DESIGN.md's own note
   *  that a new label needs a key in both locales). Optional so a section can render
   *  without one if it never gets a label. */
  label?: string;
  first?: boolean;
  /**
   * The org's own name is the page's most prominent heading (28px, DESIGN.md 5.4); the
   * seven section headings that follow it are one step down (21px). Both stay `<h2>`:
   * this page carries no `<h1>` of its own (only the board's crisis title does), so a
   * flat, single level keeps the outline honest rather than inventing a rank.
   */
  headingClassName?: string;
  /** Content next to the heading, e.g. the "Alle Quellen anzeigen" switch in the header. */
  headingExtra?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      aria-labelledby={headingId}
      className={`dossier-panel break-inside-avoid ${first ? "" : "mt-8"}`}
    >
      {label ? <span className="dossier-panel-label">{label}</span> : null}
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id={headingId} className={`${headingClassName} text-ink`}>
          {heading}
        </h2>
        {headingExtra}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}
