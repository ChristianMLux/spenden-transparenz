// Reads the design tokens straight out of globals.css and fails the build if any
// contrast ratio drops below what DESIGN.md promises.
//
// The parity check is the important one. DESIGN.md rule A1: the mark for
// "nicht gefunden" must never read weaker than the mark for a documented value. A
// transposed hex digit would break that silently, so it is a test, not a comment.
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

function tokens(label, blockRe) {
  const block = css.match(blockRe);
  if (!block) throw new Error(`globals.css: could not find the ${label} token block`);
  const out = {};
  for (const [, k, v] of block[1].matchAll(/--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})/g)) out[k] = v;
  if (Object.keys(out).length === 0) throw new Error(`globals.css: ${label} block has no tokens`);
  return out;
}

const lin = (c) => {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};
const lum = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
};
const ratio = (a, b) => {
  const [hi, lo] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (hi + 0.05) / (lo + 0.05);
};

const REQUIRED = [
  "bg",
  "surface",
  "ink",
  "muted",
  "rule",
  "accent",
  "mark-doc",
  "mark-doc-tint",
  "mark-open",
  "mark-open-tint",
  "warn",
  // Variant C, "Kontor": the dark navy chrome shared by the masthead, figure strip and
  // filter rail, plus its own ink/muted/rule triad and the structural row-hover tint.
  "chrome",
  "chrome-ink",
  "chrome-muted",
  "chrome-rule",
  "row-hover",
];

const light = tokens("light :root/.light", /^:root,\n\.light \{\n([\s\S]*?)^\}/m);
const dark = tokens("dark .dark", /^\.dark \{\n([\s\S]*?)^\}/m);
const darkNoJs = tokens(
  "dark prefers-color-scheme",
  /^ {2}html:not\(\.light\):not\(\.dark\) \{\n([\s\S]*?)^ {2}\}/m,
);

const fails = [];
const report = [];
const check = (name, got, min) => {
  report.push(`${name.padEnd(34)} ${got.toFixed(2)}:1  (min ${min})`);
  if (got < min) fails.push(`${name}: ${got.toFixed(2)}:1, needs at least ${min}:1`);
};

for (const [theme, t] of [
  ["light", light],
  ["dark", dark],
]) {
  const missing = REQUIRED.filter((k) => !t[k]);
  if (missing.length) {
    fails.push(`${theme}: missing tokens ${missing.join(", ")}`);
    continue;
  }
  check(`${theme}: ink on bg`, ratio(t.ink, t.bg), 7);
  check(`${theme}: ink on surface`, ratio(t.ink, t.surface), 7);
  check(`${theme}: muted on bg`, ratio(t.muted, t.bg), 4.5);
  check(`${theme}: accent on bg (focus)`, ratio(t.accent, t.bg), 3);
  check(`${theme}: warn on bg`, ratio(t.warn, t.bg), 4.5);

  // Variant C, "Kontor": the wordmark, figure numerals and filter-rail labels all sit
  // directly on --chrome, so these two are load-bearing the same way ink-on-bg is.
  check(`${theme}: chrome-ink on chrome`, ratio(t["chrome-ink"], t.chrome), 7);
  check(`${theme}: chrome-muted on chrome`, ratio(t["chrome-muted"], t.chrome), 4.5);

  const doc = ratio(t["mark-doc"], t["mark-doc-tint"]);
  const open = ratio(t["mark-open"], t["mark-open-tint"]);
  check(`${theme}: mark-doc on its tint`, doc, 4.5);
  check(`${theme}: mark-open on its tint`, open, 4.5);

  const delta = Math.abs(doc - open);
  report.push(`${(theme + ": mark parity delta").padEnd(34)} ${delta.toFixed(2)}     (max 0.50)`);
  if (delta > 0.5) {
    fails.push(
      `${theme}: mark parity broken. Documented reads ${doc.toFixed(2)}:1, open reads ` +
        `${open.toFixed(2)}:1, delta ${delta.toFixed(2)}. "nicht gefunden" would look ` +
        `weaker than a found value, which DESIGN.md forbids.`,
    );
  }
}

// Without JavaScript no theme class is set, so the dark palette also lives in a
// prefers-color-scheme block. Duplicated values drift; this makes drift a build error.
for (const k of new Set([...Object.keys(dark), ...Object.keys(darkNoJs)])) {
  if (dark[k] !== darkNoJs[k]) {
    fails.push(
      `dark palette drift on --${k}: .dark says ${dark[k] ?? "nothing"}, ` +
        `prefers-color-scheme says ${darkNoJs[k] ?? "nothing"}`,
    );
  }
}
report.push(`${"dark blocks in sync".padEnd(34)} ${Object.keys(dark).length} tokens`);

console.log(report.join("\n"));
if (fails.length) {
  console.error("\nCONTRAST FAILURES:\n  " + fails.join("\n  "));
  process.exit(1);
}
console.log("\ncontrast ok");
