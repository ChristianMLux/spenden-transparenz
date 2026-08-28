// Fails the build if any page's first-load JavaScript exceeds the budget.
//
// Turbopack's build-manifest has no per-app-route entry, so this measures the thing that
// actually matters instead of a proxy for it: every module <script src> in each
// prerendered HTML file, gzipped, which is what a browser downloads before the page is
// interactive. noModule scripts are the legacy polyfill bundle that a current browser
// never fetches; counting them would overstate first load by around 39 KB.
//
// Prints every page on every run, pass or fail, so a pull request can quote the figure
// rather than assert one.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { gzipSync } from "node:zlib";

// The spec names 110 KB. Measured, Next 16 App Router with cacheComponents plus next-intl
// costs about 127 KB gz on a bare redirect and 145.9 KB on a trust page that renders the
// real shell and nothing else, so 110 is not reachable on this stack and pretending
// otherwise would only mean a permanently red gate.
//
// 155 KB is the ceiling the product owner set for public pages. It is a real constraint,
// not a rounding of whatever we happened to ship: the board sits at 151.2 and the
// organisation pages at 147.4, the latter only because Radix Popover is deferred to first
// interaction instead of being loaded up front. Undo that deferral and this gate goes red
// again, which is the point of keeping the number close.
//
// Raising it is a product owner decision, not a developer one.
const BUDGET_BYTES = 155 * 1024;

const appDir = join(process.cwd(), ".next", "server", "app");
if (!existsSync(appDir)) {
  console.error(`Missing ${appDir}. Run \`npm run build\` first.`);
  process.exit(1);
}

function htmlFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...htmlFiles(full));
    else if (entry.name.endsWith(".html")) out.push(full);
  }
  return out;
}

const sizeCache = new Map();
function scriptSize(src) {
  if (sizeCache.has(src)) return sizeCache.get(src);
  const file = join(process.cwd(), ".next", src.replace(/^\/_next\//, ""));
  const size = existsSync(file)
    ? { gz: gzipSync(readFileSync(file), { level: 9 }).byteLength, raw: statSync(file).size }
    : { gz: 0, raw: 0 };
  sizeCache.set(src, size);
  return size;
}

const rows = [];
for (const file of htmlFiles(appDir)) {
  const html = readFileSync(file, "utf8");
  const srcs = new Set();
  for (const match of html.matchAll(/<script([^>]*)>/g)) {
    const attrs = match[1];
    if (/nomodule/i.test(attrs)) continue;
    const src = attrs.match(/\ssrc="([^"]+)"/);
    if (src && src[1].startsWith("/_next/")) srcs.add(src[1]);
  }

  let gz = 0;
  let raw = 0;
  for (const src of srcs) {
    const size = scriptSize(src);
    gz += size.gz;
    raw += size.raw;
  }

  rows.push({
    page: "/" + relative(appDir, file).replace(/\\/g, "/").replace(/\.html$/, ""),
    scripts: srcs.size,
    gz,
    raw,
  });
}

rows.sort((a, b) => b.gz - a.gz);

console.log("first load JS per prerendered page (module scripts, gzipped)");
for (const r of rows) {
  const gz = (r.gz / 1024).toFixed(1).padStart(7);
  const raw = (r.raw / 1024).toFixed(1).padStart(7);
  console.log(`  ${gz} KB gz  (${raw} KB raw, ${String(r.scripts).padStart(2)} scripts)  ${r.page}`);
}

if (rows.length === 0) {
  console.error("No prerendered HTML found. Something is wrong with the build.");
  process.exit(1);
}
if (rows[0].scripts === 0) {
  console.error("Found no module scripts at all. The extraction is broken, not the bundle.");
  process.exit(1);
}

// /dev/* is internal, carries noindex and is not in the sitemap, so it is measured and
// printed but does not gate the build.
const worst = rows.find((r) => !r.page.includes("/dev/"));
if (!worst) {
  console.error("No public page found to check.");
  process.exit(1);
}

console.log(`\nbudget ${(BUDGET_BYTES / 1024).toFixed(0)} KB gz`);
if (worst.gz > BUDGET_BYTES) {
  console.error(
    `\nOVER BUDGET: ${worst.page} loads ${(worst.gz / 1024).toFixed(1)} KB gz, ` +
      `budget is ${(BUDGET_BYTES / 1024).toFixed(0)} KB.`,
  );
  process.exit(1);
}
console.log(`worst page is ${(worst.gz / 1024).toFixed(1)} KB gz. ok`);
