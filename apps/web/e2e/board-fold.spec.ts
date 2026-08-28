import { expect, test } from "@playwright/test";

/**
 * The board's first screen must show organisations, not only the instrument for finding
 * them. The first version stacked every filter group in one full-width column, so at
 * 1280x900 a reader saw the heading, the figures and about fifteen checkboxes and not one
 * organisation. Every screenshot taken at the time was fullPage, which is exactly why
 * nobody noticed.
 */
test.describe("board fold", () => {
  test("the first organisation is fully visible and the second's heading is visible at 1280x900", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    const res = await page.goto("/de/krise/nepal-flut-2026");
    expect(res?.status()).toBe(200);
    await page.waitForLoadState("networkidle");

    const m = await page.evaluate(() => {
      const arts = [...document.querySelectorAll("article")];
      const first = arts[0]?.getBoundingClientRect();
      const secondHeading = arts[1]?.querySelector("h3")?.getBoundingClientRect();
      return {
        firstTop: first?.top ?? Number.POSITIVE_INFINITY,
        firstBottom: first?.bottom ?? Number.POSITIVE_INFINITY,
        secondHeadingBottom: secondHeading?.bottom ?? Number.POSITIVE_INFINITY,
      };
    });

    // The list has to begin in the upper half of the first screen. Before the rail it
    // started around y=1140, below a full column of checkboxes.
    expect(m.firstTop).toBeLessThan(500);
    // The acceptance the product owner set, after reading the delivered fold: the first
    // organisation complete, and enough of the second to see whose row it is. A literal
    // three would mean giving up the scope sentence or the figure row, and those are the
    // page's honesty statement, so they stay.
    expect(m.firstBottom).toBeLessThan(900);
    expect(m.secondHeadingBottom).toBeLessThan(900);
  });

  test("no invented map is shipped", async ({ page }) => {
    // The locator was a bezier blob its own comment called a "simplified silhouette" of
    // Nepal, with district marks placed roughly. On a product whose whole claim is that
    // nothing is invented, a fabricated map is the worst possible first graphic. The
    // districts are plain links now. A real outline is post-v1, from an attributable
    // source with its licence.
    const res = await page.goto("/nepal-locator.svg");
    expect(res?.status()).toBe(404);

    await page.goto("/de/krise/nepal-flut-2026");
    await expect(page.locator("svg[viewBox='0 0 180 140']")).toHaveCount(0);
  });

  test("the figure for organisations without a response filters to exactly those", async ({ page }) => {
    await page.goto("/de/krise/nepal-flut-2026");
    await page.waitForLoadState("networkidle");
    await page.getByRole("link", { name: /9 ohne gefundene Reaktion/ }).click();
    await expect(page.getByText("9 von 44 Organisationen")).toBeVisible();
    await expect(page.locator("article")).toHaveCount(9);
  });
});
