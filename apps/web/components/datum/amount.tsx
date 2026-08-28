import { useTranslations } from "next-intl";
import type { AmountBasis } from "@/lib/types";

export interface AmountParts {
  number: string;
  currency: string;
  basisKey: string;
}

/**
 * There is no way to render a bare figure with this component: `basis` is required, so
 * "CHF 25.000.000" cannot compile without also saying what kind of 25 million it is.
 * The rule that amounts are never naked is enforced by the type checker rather than by
 * whoever happens to review the pull request.
 */
export function amountParts(input: {
  amount: number;
  currency: string;
  basis: AmountBasis;
  locale: "de" | "en";
}): AmountParts {
  return {
    number: new Intl.NumberFormat(input.locale === "de" ? "de-DE" : "en-GB").format(input.amount),
    currency: input.currency,
    basisKey: `amount.basis.${input.basis}`,
  };
}

export function Amount({
  amount,
  currency,
  basis,
  locale,
}: {
  amount: number;
  currency: string;
  basis: AmountBasis;
  locale: "de" | "en";
}) {
  const t = useTranslations("common");
  const parts = amountParts({ amount, currency, basis, locale });
  return (
    <span className="text-ink">
      <span className="tabular-nums">
        {parts.currency} {parts.number}
      </span>{" "}
      <span>{t(parts.basisKey)}</span>
    </span>
  );
}
