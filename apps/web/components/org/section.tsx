import type { ReactNode } from "react";

/**
 * The one shared frame for the eight sections of the org page: a 1px rule plus 32px of
 * space above (DESIGN.md 5.5), a heading that carries the section's accessible name, and
 * `break-inside-avoid` so a section never splits across a printed page. The first
 * section (the header) opts out of the top rule since it opens the page.
 *
 * Every heading is preceded by a 3px accent rule (BRIEF, "Amtsblatt"): a short bar in
 * the single accent, aria-hidden since it carries no information a screen reader needs
 * beyond the heading text itself. It is the one place other than the masthead band and
 * the filter chips that colour appears on this page, and it marks a section the same
 * way at the top of the org header as at the top of every section that follows.
 */
export function OrgSection({
  headingId,
  heading,
  first = false,
  headingClassName = "text-lg",
  headingExtra,
  children,
}: {
  headingId: string;
  heading: ReactNode;
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
      className={`break-inside-avoid ${first ? "" : "mt-8 border-t border-rule pt-8"}`}
    >
      <div className="h-[3px] w-10 bg-accent" aria-hidden="true" />
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-3">
        <h2 id={headingId} className={`${headingClassName} text-ink`}>
          {heading}
        </h2>
        {headingExtra}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}
