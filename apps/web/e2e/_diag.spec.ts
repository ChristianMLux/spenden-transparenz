import { test } from "@playwright/test";

test("diag", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/de/krise/nepal-flut-2026");
  await page.waitForLoadState("networkidle");
  const data = await page.evaluate(() => {
    function r(el: Element | null | undefined, label: string) {
      if (!el) return { label, missing: true };
      const rect = el.getBoundingClientRect();
      return { label, top: Math.round(rect.top), bottom: Math.round(rect.bottom), h: Math.round(rect.height) };
    }
    const panels = [...document.querySelectorAll("main .dossier-panel")];
    const paras = [...document.querySelectorAll("main p")];
    const dataStand = paras.find((p) => p.textContent?.includes("Daten-Stand"));
    const districtLine = paras.find((p) => p.textContent?.includes("Distrikte mit"));
    return {
      band1: r(document.querySelector("header > div:nth-child(1)"), "band1"),
      band2: r(document.querySelector("header > div:nth-child(2)"), "band2"),
      h1: r(document.querySelector("h1"), "h1"),
      details: r(document.querySelector("#helfen"), "details"),
      figuresPanel: r(panels[1], "figuresPanel"),
      listPanel: r(panels[2], "listPanel"),
      dataStandP: r(dataStand, "dataStand"),
      districtP: r(districtLine, "districtLine"),
      gridWrap: r(document.querySelector("main .grid.gap-6"), "gridWrap"),
      rail: r(document.querySelector("main .dossier-rail"), "rail"),
      firstArticle: r(document.querySelector("article"), "firstArticle"),
    };
  });
  console.log(JSON.stringify(data, null, 2));
});
