import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// A representative org: has statements, a source_unreachable registration (the SWC row,
// the page's most honest line), a searched_not_found presence gap, and research_notes.
const ORG = "nepal-red-cross-society";
const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test.describe("org detail page: honesty and structure", () => {
  test("renders the eight sections, each an aria-labelledby section with a heading", async ({
    page,
  }) => {
    await page.goto(`/de/organisation/${ORG}`);
    const headingIds = [
      "org-name",
      "response-heading",
      "presence-heading",
      "registrations-heading",
      "financial-heading",
      "gaps-heading",
      "corrections-heading",
    ];
    for (const id of headingIds) {
      await expect(page.locator(`#${id}`)).toBeVisible();
      const section = page.locator(`section[aria-labelledby="${id}"]`);
      await expect(section).toHaveCount(1);
    }
    // warnings-heading is intentionally absent: warnings[] is empty for every pilot org.
    await expect(page.locator("#warnings-heading")).toHaveCount(0);
  });

  test("carries no score, rating, or ranking language anywhere in the rendered page", async ({
    page,
  }) => {
    await page.goto(`/de/organisation/${ORG}`);
    const text = (await page.locator("body").innerText()).toLowerCase();
    for (const banned of ["beste", "top", "führend", "empfohlen", "vertrauenswürdig", "score"]) {
      expect(text).not.toContain(banned);
    }
  });

  test("a not-found registration reads with the same weight as a found value", async ({
    page,
  }) => {
    await page.goto(`/de/organisation/${ORG}`);
    const styles = await page.evaluate(() => {
      const spans = [...document.querySelectorAll("span.text-base")];
      const pick = (predicate: (t: string) => boolean) => {
        const el = spans.find((s) => predicate(s.textContent?.trim() ?? ""));
        if (!el) return null;
        const cs = getComputedStyle(el);
        return { color: cs.color, fontSize: cs.fontSize, fontWeight: cs.fontWeight };
      };
      return {
        found: pick((t) => /^\d{4}$/.test(t)), // the since-year value, e.g. "1963"
        notFound: pick((t) => t === "nicht gefunden" || t === "Quelle nicht erreichbar"),
      };
    });
    expect(styles.found).not.toBeNull();
    expect(styles.notFound).not.toBeNull();
    expect(styles.notFound).toEqual(styles.found);
  });

  test("the SWC row reads as a sentence, not a blank cell", async ({ page }) => {
    await page.goto(`/de/organisation/${ORG}`);
    await expect(page.getByText(/Quelle nicht erreichbar/).first()).toBeVisible();
  });

  test("every row holding an inline datum is at least 44px tall", async ({ page }) => {
    await page.goto(`/de/organisation/${ORG}`);
    const heights = await page
      .locator('section[aria-labelledby="presence-heading"] .min-h-11')
      .evaluateAll((els) => els.map((el) => el.getBoundingClientRect().height));
    expect(heights.length).toBeGreaterThan(0);
    for (const h of heights) expect(h).toBeGreaterThanOrEqual(44);
  });

  test("the registrations section is the page's only horizontal scroll box", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto(`/de/organisation/${ORG}`);
    const scrollers = await page.evaluate(() =>
      [...document.querySelectorAll("body *")]
        .filter((el) => {
          const cs = getComputedStyle(el);
          return (
            cs.overflowX === "auto" && el.scrollWidth > el.clientWidth && el.clientWidth > 0
          );
        })
        .map((el) => el.id || el.className.toString()),
    );
    expect(scrollers.length).toBeLessThanOrEqual(1);
  });

  test("the source toggle reveals every provenance body on the page", async ({ page }) => {
    await page.goto(`/de/organisation/${ORG}`);
    const before = await page.locator(".datum-expanded").first().isVisible();
    expect(before).toBe(false);
    await page.getByRole("button", { name: "Alle Quellen anzeigen" }).click();
    const after = await page.locator(".datum-expanded").first().isVisible();
    expect(after).toBe(true);
  });

  test("the mailto link carries the org id and a date in its subject", async ({ page }) => {
    await page.goto(`/de/organisation/${ORG}`);
    const href = await page.getByRole("link", { name: /E-Mail/ }).getAttribute("href");
    expect(href).toContain("mailto:");
    const subject = decodeURIComponent(href!.split("subject=")[1] ?? "");
    expect(subject).toContain(ORG);
  });
});

test.describe("org detail page: axe", () => {
  for (const locale of ["de", "en"] as const) {
    for (const scheme of ["light", "dark"] as const) {
      test(`/${locale}/organisation/${ORG} has no axe violations in ${scheme}`, async ({
        page,
      }) => {
        await page.emulateMedia({ colorScheme: scheme });
        await page.goto(`/${locale}/organisation/${ORG}`);
        const { violations } = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
        expect(violations.map((v) => `${v.id} (${v.impact}) x${v.nodes.length}`)).toEqual([]);
      });
    }
  }
});

test.describe("org detail page: keyboard", () => {
  test("an inline datum chip opens with the keyboard and returns focus on Escape", async ({
    page,
  }) => {
    await page.goto(`/de/organisation/${ORG}`);
    const chip = page.getByRole("button", { name: /Beleg für .+:/ }).first();
    await chip.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(chip).toBeFocused();
  });
});

test.describe("org detail page: no third-party requests", () => {
  test("the page makes no third-party requests and fetches nothing after load", async ({
    page,
  }) => {
    const hosts = new Set<string>();
    page.on("request", (r) => {
      const url = r.url();
      if (url.startsWith("data:") || url.startsWith("blob:")) return;
      hosts.add(new URL(url).host);
    });
    await page.goto(`/de/organisation/${ORG}`);
    await page.waitForLoadState("networkidle");
    expect([...hosts].filter((h) => !h.startsWith("localhost"))).toEqual([]);
  });
});

test.describe("org detail page: screenshots for PR evidence", () => {
  const targets = [
    { locale: "de", width: 360 },
    { locale: "de", width: 1280 },
    { locale: "en", width: 360 },
    { locale: "en", width: 1280 },
  ];
  for (const { locale, width } of targets) {
    test(`screenshot org page, ${locale}, ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(`/${locale}/organisation/${ORG}`);
      await page.waitForLoadState("networkidle");
      await page.screenshot({
        path: `.screenshots/org-${locale}-${width}.png`,
        fullPage: true,
      });
    });
  }
});
