import { test } from "@playwright/test";

// Screenshots are the evidence for gate G0. They are written to .screenshots/, which is
// gitignored: they are proof for a pull request body, not repository content.
const PAGES = [
  { name: "datum", path: "/de/dev/datum" },
  { name: "datum-en", path: "/en/dev/datum" },
];

for (const page of PAGES) {
  test(`screenshot ${page.name}`, async ({ page: browser }, testInfo) => {
    await browser.goto(page.path);
    await browser.waitForLoadState("networkidle");
    await browser.screenshot({
      path: `.screenshots/${page.name}-${testInfo.project.name}.png`,
      fullPage: true,
    });
  });
}
