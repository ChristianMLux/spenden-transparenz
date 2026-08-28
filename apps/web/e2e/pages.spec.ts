import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import commonDe from "../messages/de/common.json";
import commonEn from "../messages/en/common.json";

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const PAGES = [
  { name: "methodik", pathDe: "/de/methodik", pathEn: "/en/methodology" },
  { name: "quellen", pathDe: "/de/quellen", pathEn: "/en/sources" },
  { name: "korrekturen", pathDe: "/de/korrekturen", pathEn: "/en/corrections" },
  { name: "impressum", pathDe: "/de/impressum", pathEn: "/en/imprint" },
  { name: "datenschutz", pathDe: "/de/datenschutz", pathEn: "/en/privacy" },
];

test.describe("screenshots", () => {
  for (const { name, pathDe, pathEn } of PAGES) {
    for (const [locale, path] of [
      ["de", pathDe],
      ["en", pathEn],
    ] as const) {
      test(`screenshot ${name} (${locale})`, async ({ page }, testInfo) => {
        await page.goto(path);
        await page.waitForLoadState("networkidle");
        await page.screenshot({
          path: `.screenshots/${name}-${locale}-${testInfo.project.name}.png`,
          fullPage: true,
        });
      });
    }
  }
});

test.describe("axe", () => {
  for (const { name, pathDe, pathEn } of PAGES) {
    for (const [locale, path] of [
      ["de", pathDe],
      ["en", pathEn],
    ] as const) {
      for (const scheme of ["light", "dark"] as const) {
        test(`${name} (${locale}) has no axe violations in ${scheme}`, async ({ page }) => {
          await page.emulateMedia({ colorScheme: scheme });
          await page.goto(path);
          const { violations } = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
          expect(violations.map((v) => `${v.id} (${v.impact}) x${v.nodes.length}`)).toEqual([]);
        });
      }
    }
  }
});

test.describe("no horizontal overflow at 360px", () => {
  for (const { name, pathDe } of PAGES) {
    test(`${name} fits at 360px`, async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 800 });
      await page.goto(pathDe);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);
    });
  }
});

test.describe("methodik", () => {
  test("the five evidence grades are worded identically to common.datum.sentence, in both languages", async ({
    page,
  }) => {
    await page.goto("/de/methodik");
    const bodyDe = await page.textContent("body");
    for (const grade of [
      "register_confirmed",
      "externally_audited",
      "self_reported",
      "third_party_reported",
      "unverified",
    ] as const) {
      expect(bodyDe).toContain(commonDe.datum.sentence[grade]);
    }

    await page.goto("/en/methodology");
    const bodyEn = await page.textContent("body");
    for (const grade of [
      "register_confirmed",
      "externally_audited",
      "self_reported",
      "third_party_reported",
      "unverified",
    ] as const) {
      expect(bodyEn).toContain(commonEn.datum.sentence[grade]);
    }
  });

  test("states the site does not rate and does not recommend", async ({ page }) => {
    await page.goto("/de/methodik");
    await expect(page.getByText("Wir bewerten nicht und empfehlen nicht.")).toBeVisible();
  });

  test("covers all four gap_reason cases", async ({ page }) => {
    await page.goto("/de/methodik");
    const body = await page.textContent("body");
    expect(body).toContain(commonDe.datum.sentence.not_searched);
    expect(body).toContain(commonDe.datum.sentence.not_found);
    expect(body).toContain(commonDe.datum.sentence.source_unreachable);
    expect(body).toContain(commonDe.datum.sentence.not_public);
  });
});

test.describe("korrekturen", () => {
  test("is seeded with the two real sampling errors, never an empty page", async ({ page }) => {
    await page.goto("/de/korrekturen");
    await page.waitForLoadState("networkidle");
    // ResponsiveTable renders both a <table> (md+) and a stacked <dl> (mobile) in the
    // same DOM, toggled by CSS visibility rather than removed from the tree, so this
    // reads textContent (present either way) instead of asserting visibility on a
    // locator that legitimately matches twice, once hidden.
    const body = await page.textContent("body");
    expect(body).toContain("Non-Resident Nepali Association");
    expect(body).toContain("UNICEF Nepal");
    expect(body?.toLowerCase()).not.toContain("bisher keine korrekturen");
    expect(body?.toLowerCase()).not.toContain("no corrections yet");
  });
});

test.describe("impressum and datenschutz", () => {
  for (const path of ["/de/impressum", "/de/datenschutz"]) {
    test(`${path} shows a visible placeholder, not lorem ipsum, and is noindex`, async ({ page }) => {
      await page.goto(path);
      const body = await page.textContent("body");
      expect(body?.toLowerCase()).not.toContain("lorem ipsum");
      expect(body).toMatch(/ergänzt/);
      const robots = page.locator('meta[name="robots"]');
      await expect(robots).toHaveAttribute("content", /noindex/);
    });
  }
});

test.describe("quellen", () => {
  test("the dataset download is a real static file, not an endpoint response", async ({ page, request }) => {
    await page.goto("/de/quellen");
    const link = page.getByRole("link", { name: /orgs-nepal-2026\.json/ });
    await expect(link).toBeVisible();
    const href = await link.getAttribute("href");
    expect(href).toBe("/datasets/orgs-nepal-2026.json");
    const res = await request.get(href!);
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("json");
  });
});

test.describe("SEO", () => {
  test("methodik sets canonical and DE/EN alternates that point at each other", async ({ page }) => {
    await page.goto("/de/methodik");
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /\/de\/methodik$/);
    await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveAttribute("href", /\/en\/methodology$/);

    await page.goto("/en/methodology");
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /\/en\/methodology$/);
    await expect(page.locator('link[rel="alternate"][hreflang="de"]')).toHaveAttribute("href", /\/de\/methodik$/);
  });

  test("robots.txt disallows /dev and /api and allows everything else", async ({ request }) => {
    const res = await request.get("/robots.txt");
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toMatch(/Disallow:\s*\/dev/);
    expect(body).toMatch(/Disallow:\s*\/api/);
    expect(body).toMatch(/Allow:\s*\//);
  });

  test("sitemap.xml lists the board and the trust pages in both locales, never /dev/datum", async ({
    request,
  }) => {
    const res = await request.get("/sitemap.xml");
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toContain("/de/krise/nepal-flut-2026");
    expect(body).toContain("/en/crisis/nepal-flut-2026");
    expect(body).toContain("/de/methodik");
    expect(body).toContain("/en/methodology");
    expect(body).not.toContain("/dev/datum");
    // The two noindex pages do not belong in a sitemap.
    expect(body).not.toContain("/impressum");
    expect(body).not.toContain("/datenschutz");
  });

  test("opengraph-image renders per locale and carries no photo, only the site's own tokens", async ({
    page,
    request,
  }) => {
    // Lives under app/[locale]/, not app/, because the locale proxy redirects any
    // extensionless path to add a locale prefix and a root-level file only answers
    // un-prefixed. Read the real URL Next injects rather than assuming one.
    await page.goto("/de/methodik");
    const ogImage = page.locator('meta[property="og:image"]');
    const imageUrl = await ogImage.getAttribute("content");
    expect(imageUrl).toMatch(/\/de\/opengraph-image/);
    const res = await request.get(imageUrl!);
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("image/png");
  });
});

test.describe("no third-party requests", () => {
  test("methodik makes no third-party requests and fetches no data after load", async ({ page }) => {
    const hosts = new Set<string>();
    page.on("request", (r) => {
      const url = r.url();
      if (url.startsWith("data:") || url.startsWith("blob:")) return;
      hosts.add(new URL(url).host);
    });
    await page.goto("/de/methodik");
    await page.waitForLoadState("networkidle");
    expect([...hosts].filter((h) => !h.startsWith("localhost"))).toEqual([]);

    const later: string[] = [];
    page.on("request", (r) => later.push(r.url()));
    await page.waitForTimeout(1000);
    expect(later).toEqual([]);
  });
});
