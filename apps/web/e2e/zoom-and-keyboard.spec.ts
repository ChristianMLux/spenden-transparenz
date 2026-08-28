import { expect, test } from "@playwright/test";

// Two gate criteria that are easy to assert and easy to get wrong: the page must survive
// 200% zoom without sideways scrolling, and the Datum popover must be operable from the
// keyboard alone.

test.describe("200 percent zoom", () => {
  // WCAG 1.4.10 reflow is measured at 320 CSS px wide, which is what a 1280px window
  // becomes at 400% zoom. 640px is the 200% case the spec names. Both are checked.
  for (const width of [640, 320]) {
    test(`no horizontal scrolling at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/de/dev/datum");
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        // Which element sticks out, so a failure names the culprit instead of a number.
        culprits: [...document.querySelectorAll("*")]
          .filter((el) => el.getBoundingClientRect().right > document.documentElement.clientWidth + 1)
          .slice(0, 5)
          .map((el) => `${el.tagName.toLowerCase()}.${(el.className || "").toString().slice(0, 60)}`),
      }));
      expect(overflow.culprits).toEqual([]);
      expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);
    });
  }
});

test.describe("keyboard path", () => {
  test("the first tab stop is the skip link, and it reveals itself", async ({ page }) => {
    await page.goto("/de/dev/datum");
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toHaveAttribute("href", "#inhalt");
    // sr-only until focused, so it has to have real size once it is.
    const box = await focused.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThan(10);
  });

  test("a Datum chip opens with the keyboard and Escape returns focus to it", async ({ page }) => {
    await page.goto("/de/dev/datum");

    const chip = page.getByRole("button", { name: /Beleg für Einnahmen: Register/ }).first();
    await chip.focus();
    await expect(chip).toHaveAttribute("aria-expanded", "false");

    await page.keyboard.press("Enter");
    await expect(chip).toHaveAttribute("aria-expanded", "true");

    // Radix labels the content from the heading DatumBody renders, so the dialog has a
    // name. An unnamed dialog is the failure this asserts against.
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAccessibleName(/Beleg: Einnahmen/);

    await page.keyboard.press("Escape");
    await expect(chip).toHaveAttribute("aria-expanded", "false");
    await expect(chip).toBeFocused();
  });

  test("every Datum chip has a name that says which field it belongs to", async ({ page }) => {
    await page.goto("/de/dev/datum");
    const names = await page.getByRole("button").evaluateAll((els) =>
      els.map((el) => el.getAttribute("aria-label") ?? el.textContent?.trim() ?? ""),
    );
    expect(names.length).toBeGreaterThan(5);
    // "Register" on its own appears many times on an org page and tells a screen reader
    // user nothing. Every chip name has to carry its field.
    for (const name of names) {
      expect(name).toMatch(/Beleg für .+: .+/);
    }
  });

  test("a not-found value is rendered with the same classes as a found one", async ({ page }) => {
    await page.goto("/de/dev/datum");
    const styles = await page.evaluate(() => {
      const spans = [...document.querySelectorAll("span.text-base")];
      const pick = (text: string) => {
        const el = spans.find((s) => s.textContent?.trim() === text);
        if (!el) return null;
        const cs = getComputedStyle(el);
        return {
          color: cs.color,
          fontSize: cs.fontSize,
          fontWeight: cs.fontWeight,
          fontStyle: cs.fontStyle,
          opacity: cs.opacity,
          textDecorationLine: cs.textDecorationLine,
        };
      };
      return { value: pick("GBP 1.842.000"), notFound: pick("nicht gefunden") };
    });

    expect(styles.value).not.toBeNull();
    expect(styles.notFound).not.toBeNull();
    // The single most important rule in the product, asserted rather than reviewed.
    expect(styles.notFound).toEqual(styles.value);
  });
});
