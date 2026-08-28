import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const BOARD = { de: "/de/krise/nepal-flut-2026", en: "/en/crisis/nepal-flut-2026" };

test.describe("number line", () => {
  test('"without a found response" filters to exactly those organisations', async ({ page }) => {
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");

    const resultCount = page.locator('[aria-live="polite"]').first();

    // This figure used to apply sort=fewest-data rather than a filter, on the reasoning
    // that a "has no statement" filter could be used to hide the very organisations this
    // product insists on always showing. The instinct was right; the conclusion was not.
    // Every other figure in the row filters, and a reader who clicks a count of nine
    // expects nine rows, not forty-four reordered.
    //
    // The instinct is preserved as a property instead, asserted here and in
    // lib/filter.test.ts: the control can SHOW the organisations without a response, and
    // there is no state in which it hides one for lacking a response.
    const numberLine = page.getByRole("link", { name: /Organisationen|belegte Meldung|Distrikt|ohne gefundene Reaktion/ });
    const noResponseLink = numberLine.filter({ hasText: "ohne gefundene Reaktion" }).first();
    await expect(noResponseLink).toHaveAttribute("href", /hasResponse=0/);
    await noResponseLink.click();

    await expect(page).toHaveURL(/hasResponse=0/);
    await expect(resultCount).toHaveText(/9 von 44 Organisation/);
    await expect(page.locator("article")).toHaveCount(9);

    // Every row shown is one without a response, and each is a full row rather than a
    // greyed-out or abbreviated one.
    const articles = page.locator("article");
    for (let i = 0; i < 9; i++) {
      await expect(articles.nth(i).getByText("Keine öffentliche Reaktionsmeldung gefunden")).toBeVisible();
    }

    // Clearing brings all 44 back, so nothing was lost.
    await page.getByRole("link", { name: /44 Organisationen/ }).click();
    await expect(resultCount).toHaveText(/44 von 44 Organisation/);
  });

  test("the statements number switches to the chronological tab", async ({ page }) => {
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");

    const statementsLink = page.getByRole("link", { name: /belegte Meldung/ });
    await statementsLink.click();

    await expect(page.getByRole("tab", { name: "Chronologisch" })).toHaveAttribute("aria-selected", "true");
    await expect(page).toHaveURL(/tab=chronological/);
  });
});

test.describe("result count is live", () => {
  test("the aria-live region updates synchronously when a filter is applied", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");

    const resultCount = page.locator('[aria-live="polite"]').first();
    await expect(resultCount).toHaveText(/44 von 44 Organisation/);

    // The desktop (always-visible, not the sheet) instance of the district group: both
    // exist in the DOM at once, and only the CSS visibility differs between them (see
    // filter-bar.tsx), so the mobile copy has to be excluded explicitly rather than
    // relying on "first" to land on the visible one.
    const desktopBar = page.getByTestId("filter-bar-desktop");
    const rasuwa = desktopBar.locator("label", { hasText: /^Rasuwa/ });
    await rasuwa.locator('input[type="checkbox"]').check();

    await expect(resultCount).not.toHaveText(/44 von 44 Organisation/);
    await expect(resultCount).toHaveText(/von 44 Organisation/);
  });
});

test.describe("evidence-grade filter never looks broken", () => {
  test("options with zero matches render disabled, not hidden", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");

    const registerOption = page.getByTestId("filter-bar-desktop").locator("label", { hasText: /^Register/ });
    await expect(registerOption).toBeVisible();
    await expect(registerOption.locator('input[type="checkbox"]')).toBeDisabled();
  });
});

test.describe("keyboard order", () => {
  // Pinned to the desktop layout regardless of project: on base the filter bar lives in
  // a closed <dialog>, which browsers correctly remove from tab order, so "reaches the
  // filter" only has one unambiguous meaning at a width where the bar is inline.
  test.use({ viewport: { width: 1280, height: 900 } });

  test("filter, then a Datum provenance link, then an organisation link", async ({ page }) => {
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");

    type Stop = { tag: string; type: string | null; rel: string | null; href: string | null };
    const stops: Stop[] = [];
    for (let i = 0; i < 80; i++) {
      await page.keyboard.press("Tab");
      const stop = await page.evaluate<Stop>(() => {
        const el = document.activeElement as HTMLElement | null;
        return {
          tag: el?.tagName ?? "",
          type: el?.getAttribute("type") ?? null,
          rel: el?.getAttribute("rel") ?? null,
          href: el?.getAttribute("href") ?? null,
        };
      });
      stops.push(stop);
      if (stop.href?.includes("/organisation/")) break;
    }

    const filterIndex = stops.findIndex((s) => s.tag === "INPUT" && s.type === "checkbox");
    // The action path's "Ich möchte helfen" section (masthead nav link, then the
    // government fund's own donation channel) sits above the filter rail by design and
    // carries a legitimate rel="noopener" link of its own, so the first such link on the
    // page is no longer necessarily a statement's provenance link. The chain this test
    // actually cares about — filter, then a content provenance link, then the org link —
    // only needs the first one reachable *after* the filter.
    const datumIndex = stops.findIndex((s, i) => i > filterIndex && s.rel === "noopener");
    const orgLinkIndex = stops.findIndex((s) => s.href?.includes("/organisation/"));

    expect(filterIndex).toBeGreaterThan(-1);
    expect(datumIndex).toBeGreaterThan(filterIndex);
    expect(orgLinkIndex).toBeGreaterThan(datumIndex);
  });
});

test.describe("zero third-party requests", () => {
  for (const [locale, path] of Object.entries(BOARD)) {
    test(`${locale} board makes no third-party requests`, async ({ page }) => {
      const hosts = new Set<string>();
      page.on("request", (r) => {
        const url = r.url();
        if (url.startsWith("data:") || url.startsWith("blob:")) return;
        hosts.add(new URL(url).host);
      });
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      expect([...hosts].filter((h) => !h.startsWith("localhost"))).toEqual([]);
    });
  }
});

test.describe("axe", () => {
  const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
  for (const [locale, path] of Object.entries(BOARD)) {
    for (const scheme of ["light", "dark"] as const) {
      test(`${locale} board has no axe violations in ${scheme}`, async ({ page }) => {
        await page.emulateMedia({ colorScheme: scheme });
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
        expect(violations.map((v) => `${v.id} (${v.impact}) x${v.nodes.length}`)).toEqual([]);
      });
    }
  }
});

test.describe("the action path", () => {
  test("a missing donation channel reads with the same weight as a found one", async ({
    page,
  }) => {
    const response = await page.goto(BOARD.de);
    expect(response?.status()).toBe(200);

    // The board carries both states side by side: 34 organisations have an official
    // channel and 10 were searched without one. The rule that matters is the same rule
    // that governs every other gap in this product - the honest "we found nothing"
    // must not be rendered as a lesser thing than the value - so it is a test, not a
    // comment. Colour is allowed to differ (the two evidence tones are contrast-tuned
    // to within 0.1 of each other by scripts/contrast.mjs); size, weight, slant,
    // opacity and decoration are not.
    const styles = await page.evaluate(() => {
      const read = (el: Element) => {
        const cs = getComputedStyle(el);
        return {
          fontSize: cs.fontSize,
          fontWeight: cs.fontWeight,
          fontStyle: cs.fontStyle,
          opacity: cs.opacity,
          textDecorationLine: cs.textDecorationLine,
          textTransform: cs.textTransform,
        };
      };
      // Both states render through the same component, so both carry the same wrapper
      // class. Matching on that wrapper rather than on an exact string keeps the test
      // honest when the line grows a part: the found line reads
      // "Offizieller Spendenweg . host . date . Eigenangabe" and the missing one
      // "kein offizieller Spendenweg gefunden . date", because the date we searched on
      // is information too.
      const lines = [...document.querySelectorAll('[class*="min-h-6"]')];
      const textOf = (el: Element) => (el.textContent ?? "").trim();
      const found = lines.find((el) => textOf(el).startsWith("Offizieller Spendenweg"));
      const missing = lines.find((el) =>
        textOf(el).startsWith("kein offizieller Spendenweg gefunden"),
      );
      return {
        found: found ? read(found) : null,
        missing: missing ? read(missing) : null,
        foundIsLink: found?.tagName === "A",
        missingIsNotLink: missing?.tagName !== "A",
      };
    });

    expect(styles.found).not.toBeNull();
    expect(styles.missing).not.toBeNull();
    expect(styles.missing).toEqual(styles.found);
    expect(styles.foundIsLink).toBe(true);
    expect(styles.missingIsNotLink).toBe(true);
  });

  test("every found channel points at a page, never at a bank detail", async ({ page }) => {
    await page.goto(BOARD.de);
    const hrefs = await page
      .locator('a:has-text("Offizieller Spendenweg")')
      .evaluateAll((els) => els.map((el) => (el as HTMLAnchorElement).href));
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(href).toMatch(/^https:\/\//);
    }
    // No account number may reach the reader through the donation lines. Scoped to
    // those lines on purpose: the first version of this check scanned the whole page
    // and failed on a Nepali phone number inside a research note, which is legitimate
    // published contact detail and not a bank account. The precise guarantee - that the
    // donation data itself carries no account number anywhere, whether rendered or not -
    // is asserted at the data layer in lib/donation.test.ts.
    const lineTexts = await page
      .locator('[class*="min-h-6"]')
      .evaluateAll((els) =>
        els
          .map((el) => (el.textContent ?? "").trim())
          .filter((s) => s.toLowerCase().includes("spendenweg")),
      );
    expect(lineTexts.length).toBeGreaterThan(0);
    for (const line of lineTexts) {
      expect(line).not.toMatch(/\b[A-Z]{2}\d{2}[A-Z0-9]{10,}\b/);
      expect(line).not.toMatch(/\b\d{9,}\b/);
    }
  });

  test("the help section carries the state fund outside the organisation list", async ({
    page,
  }) => {
    await page.goto(BOARD.de);
    const help = page.locator("#helfen");
    await expect(help).toContainText("Prime Minister");
    // The count line is computed from the 44 organisations and must not have moved.
    await expect(page.getByText("44 von 44 Organisationen")).toBeVisible();
    // and the fund is not one of the rows
    const rowNames = await page.locator("article h2").allTextContents();
    expect(rowNames.some((n) => n.includes("Prime Minister"))).toBe(false);
  });
});

test.describe("screenshots", () => {
  const PAGES = [
    { name: "board-de", path: BOARD.de },
    { name: "board-en", path: BOARD.en },
  ];
  for (const p of PAGES) {
    test(`screenshot ${p.name}`, async ({ page }, testInfo) => {
      await page.goto(p.path);
      await page.waitForLoadState("networkidle");
      await page.screenshot({
        path: `.screenshots/${p.name}-${testInfo.project.name}.png`,
        fullPage: true,
      });
    });
  }
});
