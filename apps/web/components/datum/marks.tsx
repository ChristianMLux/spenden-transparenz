import type { SVGProps } from "react";

/**
 * Nine hand-drawn 12px marks. There is deliberately no icon library in this project:
 * the only icons needed are these plus a handful of controls, a recognisable icon set is
 * one of the tells of a templated interface, and every avoided dependency is headroom
 * against the 110 KB first-load budget.
 *
 * A mark never carries meaning on its own. It always sits next to its word, so a reader
 * who cannot distinguish the drawings loses nothing.
 *
 * The not_found mark is a complete rectangle at the same stroke weight as every other
 * mark: an empty frame, never a dash, a cross or a strike. Absence is drawn, not omitted.
 */
export type MarkKey =
  | "register_confirmed"
  | "externally_audited"
  | "self_reported"
  | "third_party_reported"
  | "unverified"
  | "not_found"
  | "not_searched"
  | "source_unreachable"
  | "not_public"
  | "stale";

const BOX = "M1.5 2.5H10.5V9.5H1.5Z";

function paths(k: MarkKey) {
  switch (k) {
    case "register_confirmed":
      // A sheet with a seal.
      return (
        <>
          <path d={BOX} />
          <circle cx="8.4" cy="7.6" r="1.15" fill="currentColor" stroke="none" />
        </>
      );
    case "externally_audited":
      // A sheet that has been signed off. The tick sits inside the frame and refers to
      // the document, never to the organisation.
      return (
        <>
          <path d={BOX} />
          <path d="M3.6 6.1L5.2 7.7L8.4 4.5" />
        </>
      );
    case "self_reported":
      // A sheet that speaks for itself.
      return (
        <>
          <path d={BOX} />
          <path d="M3.6 9.5L3 11.4L5.6 9.5" />
        </>
      );
    case "third_party_reported":
      // Two sheets: someone else reporting about someone.
      return (
        <>
          <path d="M3.6 4V1.5H11V7.4" />
          <path d="M1 4H8.4V10.5H1Z" />
        </>
      );
    case "unverified":
      // The frame does not close at the bottom: found, but the source does not carry it.
      return (
        <>
          <path d="M1.5 9.5V2.5H10.5V9.5" />
          <path d="M1.5 9.5H10.5" strokeDasharray="1.7 1.3" />
        </>
      );
    case "not_found":
    case "not_searched":
      // Same weight, same size, same frame as every found value. This is the point.
      return <path d={BOX} />;
    case "source_unreachable":
      // The frame breaks where the register should have answered.
      return <path d="M10.5 4.4V2.5H1.5V9.5H10.5V7.6" />;
    case "not_public":
      // The frame is closed across the middle: the register holds it and does not publish.
      return (
        <>
          <path d={BOX} />
          <path d="M1.5 6H10.5" />
        </>
      );
    case "stale":
      // A clock. Says the reading is old, never that it is wrong.
      return (
        <>
          <circle cx="6" cy="6" r="4" />
          <path d="M6 3.4V6L7.9 7.2" />
        </>
      );
  }
}

export function Mark({ mark, ...rest }: { mark: MarkKey } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 12 12"
      width="12"
      height="12"
      aria-hidden="true"
      focusable="false"
      stroke="currentColor"
      strokeWidth={1.25}
      strokeLinecap="square"
      strokeLinejoin="miter"
      fill="none"
      className="inline-block shrink-0 align-[-0.09em]"
      {...rest}
    >
      {paths(mark)}
    </svg>
  );
}

/** The one control glyph the shell needs. Same drawing language as the marks. */
export function ExternalMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 12 12"
      width="12"
      height="12"
      aria-hidden="true"
      focusable="false"
      stroke="currentColor"
      strokeWidth={1.25}
      strokeLinecap="square"
      fill="none"
      className="inline-block shrink-0 align-[-0.09em]"
      {...props}
    >
      <path d="M4.5 2H2V10H10V7.5" />
      <path d="M6.5 2H10V5.5" />
      <path d="M10 2L5.6 6.4" />
    </svg>
  );
}
