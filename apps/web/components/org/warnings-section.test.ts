import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import type { Datum, OrgDetail } from "@/lib/types";
import commonMessages from "@/messages/de/common.json";
import orgMessages from "@/messages/de/org.json";

import { WarningsSection } from "./warnings-section";

// warnings[] is empty in all 44 pilot records (DESIGN.md 4), so this section would ship
// untested and appear for the first time in production without a fixture. This test
// builds one directly, per the brief's explicit instruction.
function warningDatum(value: string): Datum<string> {
  return {
    value,
    is_gap: false,
    source_url: "https://example.org/notice",
    publisher: "example.org",
    retrieved_at: "2026-08-28",
    published_at: "2026-08-27",
    verification: "third_party_reported",
    quote: null,
    note: null,
    gap_reason: null,
  };
}

// next-intl types NextIntlClientProvider's props with a required `children`, which
// makes createElement's usual 3-arg form (props, ...children) fail typechecking unless
// children is also spelled out in the props object, which in turn is what
// react/no-children-prop exists to forbid. The provider's runtime behaviour does not
// care which path filled `children` in, so the props are cast to the type
// createElement expects and children are still supplied the idiomatic positional way.
type ProviderProps = ComponentProps<typeof NextIntlClientProvider>;

function render(warnings: OrgDetail["warnings"]) {
  return renderToStaticMarkup(
    createElement(
      NextIntlClientProvider,
      {
        locale: "de",
        timeZone: "Europe/Berlin",
        messages: { common: commonMessages, org: orgMessages },
      } as unknown as ProviderProps,
      createElement(WarningsSection, { warnings }),
    ),
  );
}

describe("WarningsSection", () => {
  it("renders nothing when warnings is empty, the case for every pilot record", () => {
    expect(render([])).toBe("");
  });

  it("renders a fixture warning with the --warn tone, not the --mark-open tone", () => {
    const html = render([
      { type: "regulatory_action", datum: warningDatum("A regulator opened an inquiry.") },
    ]);
    expect(html).toContain("Regulatory action");
    expect(html).toContain("A regulator opened an inquiry.");
    expect(html).toContain("text-warn");
    expect(html).toContain("border-warn");
    // The warning's own container never borrows the "ungeprüft"/open tone classes that
    // <Datum> uses for unverified or missing values: the two signals must stay visually
    // distinct (DESIGN.md 8.3, section 6).
    expect(html).not.toContain("bg-mark-open-tint");
  });

  it("humanises an unknown type string rather than looking up a translation key", () => {
    const html = render([
      { type: "sanctions_list_match", datum: warningDatum("Listed on a sanctions register.") },
    ]);
    expect(html).toContain("Sanctions list match");
  });
});
