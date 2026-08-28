"use client";

/**
 * The four figures as typographic tiles on the single warm surface (BRIEF, "Amtsblatt"):
 * a large tabular numeral over a 13px muted label, divided by 1px rules, no boxes. Each
 * tile is still exactly the filter link board-explorer.tsx already builds for the number
 * line (see numberLineTargets there) — this component only changes how that link is
 * drawn, never what it does.
 *
 * The numeral and its label come from a single already-localised ICU string
 * ("44 Organisationen" / "44 organisations") rather than a second, parallel set of
 * label-only translation keys: splitting one string in two guarantees the tile can never
 * drift out of sync with the sentence a screen reader (or a reader without JS) still
 * gets, since the underlying <a> text content is unchanged, only its visual layout.
 */
function splitFigure(text: string): { numeral: string; label: string } {
  const match = text.match(/^(\d[\d.,]*)\s*(.*)$/s);
  if (!match) return { numeral: "", label: text };
  return { numeral: match[1] ?? "", label: (match[2] ?? "").trim() };
}

export interface FigureTile {
  key: string;
  text: string;
  href: string;
  onSelect: () => void;
}

export function FigureStrip({ tiles }: { tiles: FigureTile[] }) {
  return (
    <div className="w-full border-y border-rule bg-tint">
      <div className="grid grid-cols-2 divide-y divide-rule md:grid-cols-4 md:divide-x md:divide-y-0">
        {tiles.map((tile) => {
          const { numeral, label } = splitFigure(tile.text);
          return (
            <a
              key={tile.key}
              href={tile.href}
              onClick={(e) => {
                e.preventDefault();
                tile.onSelect();
              }}
              className="group flex min-h-11 flex-col justify-center gap-1 px-4 py-0.5 no-underline focus-visible:relative focus-visible:z-10"
            >
              <span className="text-2xl leading-none text-ink">{numeral || tile.text}</span>
              {numeral ? (
                <span className="text-xs text-muted group-hover:text-ink group-hover:underline">
                  {label}
                </span>
              ) : null}
            </a>
          );
        })}
      </div>
    </div>
  );
}
