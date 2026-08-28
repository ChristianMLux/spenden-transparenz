// Copies the research artefacts from the repository root into apps/web/data so the app
// reads only from its own directory. Two reasons: Turbopack traces a dynamic
// process.cwd() walk by pulling the entire repository into the server bundle, and a
// deployment whose project root is apps/web should not reach outside it at all.
//
// The copies are gitignored. The files at the repository root stay the single source.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

const FILES = [
  ["orgs-nepal-2026.json", "orgs-nepal-2026.json"],
  ["data/raw/reliefweb/disaster_updates.json", "disaster-updates.json"],
  ["data/raw/hapi/admin2_NPL.json", "admin2-npl.json"],
  ["data/orgs/donation-channels.json", "donation-channels.json"],
];

function repoRoot() {
  let dir = resolve(process.cwd());
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, "orgs-nepal-2026.json"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error(`Could not find the repository root above ${process.cwd()}.`);
}

const root = repoRoot();
const target = join(process.cwd(), "data");
mkdirSync(target, { recursive: true });

for (const [from, to] of FILES) {
  const src = join(root, from);
  if (!existsSync(src)) throw new Error(`Missing source data file: ${src}`);
  copyFileSync(src, join(target, to));
  console.log(`data: ${from} -> data/${to}`);
}
