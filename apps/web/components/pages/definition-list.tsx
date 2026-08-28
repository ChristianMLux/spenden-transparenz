/** Term/definition rows, one hairline rule between each: the summary-list pattern from
 *  the visual brief's reference sites (gov.uk), used for the evidence grades and the
 *  gap_reason cases on /methodik. Not a table: there is no second data column to align. */
export function DefinitionList({ items }: { items: { term: string; definition: string }[] }) {
  return (
    <dl className="max-w-[68ch] divide-y divide-rule border-y border-rule">
      {items.map((item) => (
        <div key={item.term} className="grid gap-1 py-3 md:grid-cols-[10rem_1fr] md:gap-4">
          <dt className="font-semibold text-ink">{item.term}</dt>
          <dd className="text-ink">{item.definition}</dd>
        </div>
      ))}
    </dl>
  );
}
