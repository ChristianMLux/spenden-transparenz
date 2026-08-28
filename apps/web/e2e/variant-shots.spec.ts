import { test } from "@playwright/test";

// Shared WP4 screenshot harness. Identical in all three variant worktrees so the three
// directions can be compared without a viewport, a locale or a colour scheme differing
// between them. Run it with the desktop project only:
//
//   VARIANT=A npx playwright test --project=desktop e2e/variant-shots.spec.ts
//
// Playwright's own webServer config starts `npm start` and stops it again, so nothing
// here manages a server. Build first: it serves the existing .next output.
const VARIANT = process.env.VARIANT ?? "x";
const BOARD = "/de/krise/nepal-flut-2026";
const ORG = "/de/organisation/nepal-red-cross-society";

// Dark mode arrives through prefers-color-scheme: a fresh context has no theme class on
// <html>, which is the branch globals.css carries for exactly this case.
const SHOTS = [
  { name: "board-light", path: BOARD, scheme: "light" as const, fullPage: false },
  { name: "board-dark", path: BOARD, scheme: "dark" as const, fullPage: false },
  { name: "org-light", path: ORG, scheme: "light" as const, fullPage: true },
  { name: "org-dark", path: ORG, scheme: "dark" as const, fullPage: false },
];

for (const shot of SHOTS) {
  test(`variant ${VARIANT}: ${shot.name}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: shot.scheme });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(shot.path);
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: `.screenshots/variant-${VARIANT}-${shot.name}.png`,
      fullPage: shot.fullPage,
    });
  });
}
