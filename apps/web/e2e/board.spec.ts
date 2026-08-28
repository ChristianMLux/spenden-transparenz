import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const BOARD = { de: "/de/krise/nepal-flut-2026", en: "/en/crisis/nepal-flut-2026" };

test.describe("number line", () => {
  test('"without a found response" filters to exactly those organisations, never hides one for lacking a response', async ({
    page,
  }) => {
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");

    const resultCount = page.locator('[aria-live="polite"]').first();

    // A reader who clicks a count of nine expects nine rows, not forty-four reordered
    // (lead review, corrected spec): has_response=false is a real filter.
    const numberLine = page.getByRole("link", { name: /Organisationen|belegte Meldung|Distrikt|ohne gefundene Reaktion/ });
    const noResponseLink = numberLine.filter({ hasText: "ohne gefundene Reaktion" }).first();
    await expect(noResponseLink).toHaveAttribute("href", /hasResponse=false/);
    await noResponseLink.click();

    await expect(page).toHaveURL(/hasResponse=false/);
    await expect(resultCount).toHaveText(/9 von 44 Organisation/);
    const articles = page.locator("article");
    await expect(articles).toHaveCount(9);
    for (const article of await articles.all()) {
      await expect(article.getByText("Keine öffentliche Reaktionsmeldung gefunden")).toBeVisible();
    }

    // The direction that must never be possible: this filter can narrow to
    // no-response organisations, but nothing can use it to hide one. Clearing it
    // (the chip's remove button) restores all 44, none silently dropped.
    await page.getByRole("button", { name: /entfernen/i }).first().click();
    await expect(resultCount).toHaveText(/44 von 44 Organisation/);
  });

  test("each district name next to the number line links to its own single-district filter", async ({ page }) => {
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");

    const rasuwaLink = page.getByRole("link", { name: "Rasuwa" });
    await expect(rasuwaLink).toHaveAttribute("href", /districts=NP0329/);
    await rasuwaLink.click();
    await expect(page).toHaveURL(/districts=NP0329/);
    await expect(page.locator('[aria-live="polite"]').first()).not.toHaveText(/44 von 44 Organisation/);
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
    const datumIndex = stops.findIndex((s) => s.rel === "noopener");
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

test.describe("fold", () => {
  // Review acceptance: at 1280x900, at least the first three organisation articles
  // must be visible without scrolling. fullPage screenshots (above) cannot prove this;
  // only a non-fullPage capture at the exact viewport size can, which is why the first
  // attempt at this fix went unnoticed.
  test("at least three organisation articles are visible at 1280x900 without scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(BOARD.de);
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: ".screenshots/board-de-fold-1280x900.png", fullPage: false });

    const articles = page.locator("article");
    const count = await articles.count();
    let fullyVisible = 0;
    for (let i = 0; i < count; i++) {
      const box = await articles.nth(i).boundingBox();
      if (box && box.y >= 0 && box.y + box.height <= 900) fullyVisible++;
    }
    expect(fullyVisible).toBeGreaterThanOrEqual(3);
  });
});
