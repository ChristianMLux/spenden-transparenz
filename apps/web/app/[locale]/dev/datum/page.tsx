import { useLocale } from "next-intl";
import { Datum } from "@/components/datum/datum";
import type { Locale } from "@/i18n/routing";
import { SAMPLES } from "@/lib/fixtures/datum-samples";

export const metadata = { robots: { index: false, follow: false } };

const TOKENS = [
  ["--bg", "Seitengrund"],
  ["--surface", "Popover"],
  ["--ink", "Wert und nicht gefunden"],
  ["--muted", "Sekundärtext"],
  ["--rule", "Linien"],
  ["--accent", "Links und Fokus"],
  ["--mark-doc", "Marke: dokumentiert"],
  ["--mark-open", "Marke: offen"],
  ["--warn", "nur warnings[]"],
] as const;

function Matrix({ locale }: { locale: Locale }) {
  const ordered = [...SAMPLES.filter((s) => !s.variantOf), ...SAMPLES.filter((s) => s.variantOf)];

  return (
    <div className="bg-bg p-4 text-ink">
      <ul className="flex flex-col">
        {ordered.map((s) => (
          <li
            key={s.key}
            className="grid gap-2 border-b border-rule py-3 last:border-b-0 md:grid-cols-[10rem_1fr_1fr] md:gap-4"
          >
            <p className="text-xs text-muted">
              <code className="font-mono">{s.key}</code>
              {s.variantOf ? <span className="block">Variante von {s.variantOf}</span> : null}
            </p>
            <div className="min-w-0">
              <p className="mb-1 text-xs text-muted">inline</p>
              <Datum
                datum={s.datum}
                field={locale === "de" ? s.field : s.fieldEn}
                variant="inline"
                id={`${locale}-inline-${s.key}`}
              />
            </div>
            <div className="min-w-0">
              <p className="mb-1 text-xs text-muted">block</p>
              <Datum
                datum={s.datum}
                field={locale === "de" ? s.field : s.fieldEn}
                variant="block"
                id={`${locale}-block-${s.key}`}
              />
            </div>
          </li>
        ))}
      </ul>

      <h3 className="mt-8 mb-2 text-sm">Tokens</h3>
      <ul className="flex flex-wrap gap-4 text-xs text-muted">
        {TOKENS.map(([token, use]) => (
          <li key={token} className="flex items-center gap-1">
            <span
              className="inline-block size-4 border border-rule"
              style={{ backgroundColor: `var(${token})` }}
            />
            <code className="font-mono">{token}</code>
            <span>{use}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Internal. Six states, two variants, two themes on one page, so the rule that matters
 * can be checked by eye and by screenshot: the "nicht gefunden" line must be exactly as
 * dark and as heavy as the value line above it.
 */
export default function DatumMatrixPage() {
  const locale = useLocale() as Locale;

  return (
    <>
      <h1 className="mb-2">Datum</h1>
      <p className="mb-8 max-w-[68ch] text-sm text-muted">
        Interne Seite. Sechs Zustände, zwei Varianten, zwei Themes. Der Wert und das
        „nicht gefunden“ darunter müssen dieselbe Tinte, dieselbe Größe und dieselbe
        Strichstärke haben.
      </p>

      <h2 className="mb-2 text-lg">hell</h2>
      <div className="light mb-8 border border-rule">
        <Matrix locale={locale} />
      </div>

      <h2 className="mb-2 text-lg">dunkel</h2>
      <div className="dark border border-rule">
        <Matrix locale={locale} />
      </div>
    </>
  );
}
