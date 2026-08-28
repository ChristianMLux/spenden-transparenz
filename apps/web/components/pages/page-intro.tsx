/** Shared heading block for the five trust pages: title plus one optional lede sentence,
 *  in the same measure (68ch) the rest of the site uses for running text. Impressum and
 *  Datenschutz have no lede yet: they are placeholders, not pages with a scope to state. */
export function PageIntro({ title, intro }: { title: string; intro?: string }) {
  return (
    <header className="mb-8 max-w-[68ch]">
      <h1 className="mb-2">{title}</h1>
      {intro ? <p className="text-base text-muted">{intro}</p> : null}
    </header>
  );
}
