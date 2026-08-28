import { describe, expect, it } from "vitest";
import { amountParts } from "./amount";

describe("amountParts", () => {
  it("always returns a basis key next to the figure", () => {
    const p = amountParts({ amount: 25_000_000, currency: "CHF", basis: "appeal", locale: "de" });
    expect(p.number).toBe("25.000.000");
    expect(p.currency).toBe("CHF");
    expect(p.basisKey).toBe("amount.basis.appeal");
  });

  it("uses the other thousands separator in English", () => {
    const p = amountParts({ amount: 1_000_000, currency: "CHF", basis: "released", locale: "en" });
    expect(p.number).toBe("1,000,000");
  });

  it("keeps small figures readable", () => {
    expect(amountParts({ amount: 50_000, currency: "NPR", basis: "pledged", locale: "de" }).number).toBe(
      "50.000",
    );
  });

  it("carries every basis the pilot data needs", () => {
    for (const basis of ["reported", "appeal", "pledged", "raised", "released", "disbursed"] as const) {
      expect(amountParts({ amount: 1, currency: "EUR", basis, locale: "de" }).basisKey).toBe(
        `amount.basis.${basis}`,
      );
    }
  });
});
