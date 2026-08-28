import { PDFParse } from "pdf-parse";
import { expect, test } from "@playwright/test";

const ORG = "nepal-red-cross-society";

test.describe("org detail page: print", () => {
  test("a source URL that only exists inside the always-in-DOM provenance body appears in the printed text, without the expansion toggle ever being clicked", async ({
    page,
  }) => {
    await page.goto(`/de/organisation/${ORG}`);
    // The since-year presence field is an inline Datum whose full source_url is only
    // ever printed inside its .datum-expanded body (components/datum/datum-body.tsx).
    // On screen it stays display:none until the toggle is used. The toggle is never
    // touched here: that is the entire point of the always-in-DOM body, and is what
    // this test exists to prove.
    const toggle = page.getByRole("button", { name: "Alle Quellen anzeigen" });
    await expect(toggle).toHaveAttribute("aria-pressed", "false");

    const pdfBuffer = await page.pdf();
    const parser = new PDFParse({ data: pdfBuffer });
    const result = await parser.getText();
    await parser.destroy();

    expect(result.text).toContain("https://en.wikipedia.org/wiki/Nepal_Red_Cross_Society");
  });

  test("header, footer and the source toggle are hidden under print media", async ({ page }) => {
    await page.emulateMedia({ media: "print" });
    await page.goto(`/de/organisation/${ORG}`);
    await expect(page.locator("header").first()).toBeHidden();
    await expect(page.locator("footer").first()).toBeHidden();
    await expect(page.getByRole("button", { name: "Alle Quellen anzeigen" })).toBeHidden();
  });

  test("every section avoids breaking across a printed page", async ({ page }) => {
    await page.emulateMedia({ media: "print" });
    await page.goto(`/de/organisation/${ORG}`);
    const values = await page
      .locator("section[aria-labelledby]")
      .evaluateAll((els) => els.map((el) => getComputedStyle(el).breakInside));
    expect(values.length).toBeGreaterThanOrEqual(7);
    for (const v of values) expect(v).toBe("avoid");
  });

  test("the page still carries a usable @page margin", async ({ page }) => {
    // No direct DOM read of @page exists; this asserts the stylesheet declares it rather
    // than trusting the source file, by checking the sheet text Playwright can see.
    await page.goto(`/de/organisation/${ORG}`);
    const hasPageRule = await page.evaluate(() => {
      // @page sits nested inside `@media print { ... }`, so this has to recurse into
      // CSSMediaRule.cssRules, not just the sheet's own top-level rules.
      const search = (rules: CSSRuleList): boolean => {
        for (const rule of Array.from(rules)) {
          if (rule instanceof CSSPageRule && /18mm/.test(rule.style.margin)) return true;
          if (rule instanceof CSSMediaRule && search(rule.cssRules)) return true;
        }
        return false;
      };
      for (const sheet of Array.from(document.styleSheets)) {
        try {
          if (search(sheet.cssRules)) return true;
        } catch {
          // Cross-origin sheets throw on .cssRules; none exist on this page (no
          // third-party requests), so this is unreachable in practice.
        }
      }
      return false;
    });
    expect(hasPageRule).toBe(true);
  });
});
