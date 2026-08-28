import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

// The research artefacts live at the repository root and are read at build time only,
// never at request time. Resolving from cwd upwards keeps this working under
// `next build` (cwd = apps/web), under vitest (same), and from a Vercel monorepo root
// directory, without hardcoding how deep we are.
function repoRoot(): string {
  let dir = resolve(process.cwd());
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, "orgs-nepal-2026.json"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error(
    `Could not find the repository root above ${process.cwd()}. ` +
      `Looked for orgs-nepal-2026.json in that directory and its first five ancestors.`,
  );
}

const ROOT = repoRoot();

export function readRepoJson<T>(relativePath: string): T {
  const full = join(ROOT, relativePath);
  if (!existsSync(full)) throw new Error(`Missing data file: ${full}`);
  return JSON.parse(readFileSync(full, "utf8")) as T;
}
