import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
}

/**
 * A real `<table>` from `md:` up; a stacked, labelled list below it. The org
 * registrations table (WP2) is the one place in this site allowed to scroll
 * horizontally, so a table here has to reflow instead, and six columns of prose does
 * not reflow into a table at 360px. No cards: the mobile list is hairline-rule-separated
 * blocks, not bordered boxes, matching the rest of the site.
 */
export function ResponsiveTable<T extends { key: string }>({
  columns,
  rows,
}: {
  columns: Column<T>[];
  rows: T[];
}) {
  return (
    <>
      <table className="hidden w-full border-collapse text-left text-sm md:table">
        <thead>
          <tr className="border-b border-rule">
            {columns.map((c) => (
              <th key={c.key} className="py-2 pr-4 font-semibold text-ink">
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-b border-rule align-top">
              {columns.map((c) => (
                <td key={c.key} className="py-3 pr-4">
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <ul className="flex flex-col md:hidden">
        {rows.map((row) => (
          <li key={row.key} className="border-b border-rule py-4 first:pt-0">
            <dl className="flex flex-col gap-2">
              {columns.map((c) => (
                <div key={c.key}>
                  <dt className="text-xs text-muted">{c.header}</dt>
                  <dd className="text-ink">{c.cell(row)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}
