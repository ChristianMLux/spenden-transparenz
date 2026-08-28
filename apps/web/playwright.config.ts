import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // One `next start` serves the whole suite. Left uncapped, Playwright spawns a worker
  // per core and the single Node server stops answering under the load: whole spec files
  // fail with 30 second timeouts while the same files pass in isolation. That looks like
  // twenty regressions and is really one overloaded server.
  workers: process.env.CI ? 2 : 4,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "mobile",
      use: { ...devices["Desktop Chrome"], viewport: { width: 360, height: 740 } },
    },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
  ],
  // Serves an existing build; it does not produce one. `npm run test:e2e` builds first,
  // and check:bundle reads that same output.
  //
  // This used to be `npm run build && npm start` with reuseExistingServer, which meant two
  // builds writing into one .next directory while tests read from it. That produced three
  // separate false alarms in a single session: a 404 on a page that exists, six
  // organisations apparently missing from a build that emits all 44, and a link rendering
  // a query value the source cannot produce. Each looked like a serious defect; each was a
  // race. Build once, serve that build.
  webServer: {
    command: "npm start",
    url: "http://localhost:3000/de/krise/nepal-flut-2026",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
