// Runs Lighthouse against a URL and prints the four category scores.
//
// Two things make this work on Windows, and both were found the hard way:
//
// 1. chrome-launcher cannot find or launch a system Chrome here, so CHROME_PATH is
//    pointed at the Chromium that Playwright already downloaded. No extra install.
// 2. It still throws EPERM from chrome-launcher's own temp-directory cleanup AFTER the
//    audit finishes. The report is already written at that point, so the crash is
//    cosmetic and the exit code is meaningless. This reads the report file to decide
//    pass or fail instead of trusting the exit code.
//
// Usage: node scripts/lighthouse.mjs [url ...]
// Default: the German board, the English board and one organisation page, which are the
// three the budget is stated against.
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const BASE = process.env.LH_BASE_URL ?? "http://localhost:3000";
const TARGETS = process.argv.slice(2).length
  ? process.argv.slice(2)
  : [
      `${BASE}/de/krise/nepal-flut-2026`,
      `${BASE}/en/crisis/nepal-flut-2026`,
      `${BASE}/de/organisation/nepal-red-cross-society`,
    ];

const THRESHOLDS = { performance: 95, accessibility: 100, "best-practices": 95, seo: 95 };

function findPlaywrightChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const root = join(process.env.LOCALAPPDATA ?? "", "ms-playwright");
  if (!existsSync(root)) return null;
  const builds = readdirSync(root)
    .filter((d) => d.startsWith("chromium-"))
    .sort((a, b) => Number(b.split("-")[1]) - Number(a.split("-")[1]));
  for (const b of builds) {
    for (const dir of ["chrome-win64", "chrome-win"]) {
      const exe = join(root, b, dir, "chrome.exe");
      if (existsSync(exe)) return exe;
    }
  }
  return null;
}

const chrome = findPlaywrightChrome();
if (chrome) process.env.CHROME_PATH = chrome;
console.log(chrome ? `chrome: ${chrome}` : "chrome: system default");

mkdirSync(".lighthouse", { recursive: true });
let failed = false;

for (const url of TARGETS) {
  const out = join(".lighthouse", `${url.replace(/[^a-z0-9]+/gi, "-")}.json`);
  rmSync(out, { force: true });
  try {
    execFileSync(
      "npx",
      ["--yes", "lighthouse@12", url, "--only-categories=performance,accessibility,best-practices,seo",
       "--output=json", `--output-path=${out}`, "--chrome-flags=--headless=new --no-sandbox", "--quiet"],
      { stdio: "ignore", shell: true },
    );
  } catch {
    // Expected on Windows: the teardown throws after the report is written.
  }

  if (!existsSync(out)) {
    console.error(`  FAILED to produce a report for ${url}`);
    failed = true;
    continue;
  }
  const report = JSON.parse(readFileSync(out, "utf8"));
  const parts = [];
  for (const [cat, min] of Object.entries(THRESHOLDS)) {
    const score = Math.round((report.categories[cat]?.score ?? 0) * 100);
    if (score < min) failed = true;
    parts.push(`${cat} ${score}${score < min ? ` (min ${min})` : ""}`);
  }
  console.log(`  ${url}\n    ${parts.join("  ")}  LCP ${report.audits["largest-contentful-paint"].displayValue}`);
}

process.exit(failed ? 1 : 0);
