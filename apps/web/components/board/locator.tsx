/**
 * A schematic locator, not a coverage map, so it renders the geometry inline (not as an
 * <img src="/nepal-locator.svg">) rather than pulling it in as a static image asset: only
 * inline SVG can read --rule/--mark-doc/--mark-doc-tint through currentColor and fill so
 * the marks keep their contrast in the dark theme, which a byte-identical file reference
 * would freeze at its light-mode colours. public/nepal-locator.svg carries the same
 * geometry with literal hex values so the shape stays available as a standalone file.
 *
 * No interaction, no text inside, no tooltip: aria-hidden. The caption next to it is the
 * only accessible content and is what says this is a locator, not proof of coverage.
 */
export function Locator({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 180 140"
      width={180}
      height={140}
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <path
        d="M8 78 C 6 62, 22 50, 34 46 C 40 38, 36 26, 48 22 C 60 18, 66 28, 78 24
           C 90 20, 96 10, 112 12 C 128 14, 130 26, 144 30 C 160 34, 172 44, 172 58
           C 172 70, 160 72, 156 82 C 152 94, 158 104, 148 112 C 136 122, 118 116, 106 122
           C 92 128, 84 120, 70 122 C 54 124, 44 116, 32 110 C 18 104, 10 94, 8 78 Z"
        fill="var(--rule)"
        stroke="none"
      />
      <g fill="var(--mark-doc-tint)" stroke="var(--mark-doc)" strokeWidth={1.25}>
        <rect x={66} y={40} width={10} height={9} rx={1} />
        <rect x={78} y={36} width={10} height={9} rx={1} />
        <rect x={90} y={42} width={10} height={9} rx={1} />
        <rect x={80} y={50} width={10} height={9} rx={1} />
        <rect x={100} y={52} width={10} height={9} rx={1} />
        <rect x={94} y={62} width={10} height={9} rx={1} />
      </g>
    </svg>
  );
}
