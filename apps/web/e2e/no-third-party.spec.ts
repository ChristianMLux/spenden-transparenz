import { expect, test } from "@playwright/test";

test("the page makes no third-party requests", async ({ page }) => {
  const hosts = new Set<string>();
  page.on("request", (r) => {
    const url = r.url();
    if (url.startsWith("data:") || url.startsWith("blob:")) return;
    hosts.add(new URL(url).host);
  });
  await page.goto("/de/dev/datum");
  await page.waitForLoadState("networkidle");
  // Self-hosted fonts and no analytics are what make the cookie banner unnecessary.
  expect([...hosts].filter((h) => !h.startsWith("localhost"))).toEqual([]);
});

test("the page fetches no data after load", async ({ page }) => {
  await page.goto("/de/dev/datum");
  await page.waitForLoadState("networkidle");
  const later: string[] = [];
  page.on("request", (r) => later.push(r.url()));
  await page.waitForTimeout(1000);
  expect(later).toEqual([]);
});
