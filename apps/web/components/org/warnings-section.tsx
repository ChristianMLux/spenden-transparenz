import { useTranslations } from "next-intl";
import { Datum } from "@/components/datum/datum";
import type { OrgDetail } from "@/lib/types";
import { OrgSection } from "./section";

/** "regulatory_action" -> "Regulatory action". No closed set of warning types exists in
 *  any real record yet (warnings[] is empty in all 44 pilot orgs), so this humanises
 *  whatever string the data carries rather than depending on translation keys for values
 *  that would silently fall back to raw key paths the day a real warning first appears. */
function humanize(type: string): string {
  const spaced = type.replace(/[_-]+/g, " ").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * Section 6, "Öffentliche Hinweise": renders only when `warnings[]` is non-empty, which
 * is true for none of the 44 pilot records. `--warn` is the only real signal colour in
 * the product and is used here, on the left rule, visually distinct from the
 * "ungeprüft" (`--mark-open`) tone that `<Datum>` itself uses for its own source mark.
 */
export function WarningsSection({ warnings }: { warnings: OrgDetail["warnings"] }) {
  const t = useTranslations("org.warnings");

  if (warnings.length === 0) return null;

  return (
    <OrgSection headingId="warnings-heading" heading={t("heading")} label={t("label")}>
      <ul className="flex flex-col gap-4">
        {warnings.map((warning, index) => (
          <li key={`${warning.type}-${index}`} className="border-l-2 border-warn pl-3">
            <p className="text-sm text-warn">{humanize(warning.type)}</p>
            {warning.datum.value ? (
              <p className="mt-1 max-w-[68ch] text-base text-ink">{warning.datum.value}</p>
            ) : null}
            <div className="mt-1">
              <Datum
                datum={warning.datum}
                field={t("field")}
                variant="block"
                id={`warning-${index}`}
              />
            </div>
          </li>
        ))}
      </ul>
    </OrgSection>
  );
}
