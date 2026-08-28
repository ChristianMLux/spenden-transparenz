// The action path added the one thing this product had so far avoided: a link a reader
// can act on. That makes a class of copy dangerous which was previously impossible to
// write, so it is now a build gate rather than a review habit.
//
// The rule is not "never say the word recommend". The whole promise of the site is
// stated in sentences like "Sie bewertet keine Organisation und empfiehlt keine Spende"
// and "Wir bewerten nicht und empfehlen nicht" - those negations are load-bearing
// product copy and must survive. What is banned is the affirmative: an imperative call
// to action, or any phrasing that puts one organisation above another.
//
// So negated forms are removed from the text first, and only what is left is searched.
// Comments in source files are removed too: a comment explaining that this product makes
// no recommendation is not copy, and scanning it would only push authors to describe the
// rule in weaker words.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { extname, join } from "node:path";

const ROOTS = ["messages", "components", "app", "lib"];
const EXTENSIONS = new Set([".json", ".ts", ".tsx"]);

const NEGATIONS = [
  /\b(keine?n?)\s+(empfehlung(en)?|bewertung(en)?|ranking|wertung)\b/gi,
  /\bempfiehlt\s+kein\w*/gi,
  /\bempfehlen\s+kein\w*/gi,
  // German puts the negation after the verb just as often, so both orders count.
  /\bempfehl\w*\s+(nicht|nie|niemals)\b/gi,
  /\b(nicht|nie|niemals)\s+empfehl\w*/gi,
  /\b(does not|do not|doesn't|don't|will not|won't)\s+recommend\w*/gi,
  /\bno\s+(recommendation|ranking|rating|score)s?\b/gi,
  /\bnot\s+recommended\b/gi,
  /\bwithout\s+recommend\w*/gi,
];

const BANNED = [
  { pattern: /\bjetzt\s+spenden\b/i, why: "imperative call to action" },
  { pattern: /\bspenden\s+sie\b/i, why: "imperative call to action" },
  { pattern: /\bhelfen\s+sie\s+jetzt\b/i, why: "imperative call to action" },
  { pattern: /\bunterst(ü|ue)tzen\s+sie\b/i, why: "imperative call to action" },
  { pattern: /\bdonate\s+now\b/i, why: "imperative call to action" },
  { pattern: /\bgive\s+now\b/i, why: "imperative call to action" },
  { pattern: /\bempfehl\w*/i, why: "recommendation language" },
  { pattern: /\bempfohlen\b/i, why: "recommendation language" },
  { pattern: /\brecommend\w*/i, why: "recommendation language" },
  { pattern: /\b(beste|top|vertrauensw(ü|ue)rdigste)\s+organisation\b/i, why: "ranking language" },
  { pattern: /\b(best|top)\s+(charity|charities|organisation|organization)\b/i, why: "ranking language" },
  { pattern: /\bam\s+besten\s+bewertet\b/i, why: "ranking language" },
];

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "node_modules" || entry === ".next") continue;
      out.push(...walk(full));
    } else if (EXTENSIONS.has(extname(entry))) {
      out.push(full);
    }
  }
  return out;
}

const failures = [];
let scanned = 0;

for (const root of ROOTS) {
  for (const file of walk(root)) {
    // This file names every banned phrase by definition; scanning it would fail itself.
    if (file.endsWith("check-copy.mjs")) continue;
    scanned += 1;
    let text = readFileSync(file, "utf8");
    if (file.endsWith(".ts") || file.endsWith(".tsx")) {
      text = text.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/^\s*\/\/.*$/gm, " ");
    }
    for (const negation of NEGATIONS) text = text.replace(negation, " ");
    for (const { pattern, why } of BANNED) {
      const hit = text.match(pattern);
      if (hit) failures.push(`${file}: "${hit[0]}" (${why})`);
    }
  }
}

console.log(`copy: scanned ${scanned} files for call-to-action and ranking language`);
if (failures.length) {
  console.error("\nCOPY FAILURES:\n  " + failures.join("\n  "));
  console.error(
    "\nThe link label is a neutral noun phrase. A sentence that denies a recommendation is\n" +
      "allowed and expected; one that makes or implies a recommendation is not.",
  );
  process.exit(1);
}
console.log("copy ok");
