import { readFileSync } from "node:fs";
import { join } from "node:path";

// Build-time only. The paths are literals inside apps/web/data so that Turbopack traces
// exactly these four files instead of the whole repository. scripts/sync-data.mjs puts
// them there before build and before the unit tests; the originals at the repository
// root remain the single source.
const DIR = join(process.cwd(), "data");

function read<T>(name: string, full: string): T {
  try {
    return JSON.parse(readFileSync(full, "utf8")) as T;
  } catch (cause) {
    throw new Error(
      `Could not read apps/web/data/${name}. Run \`node scripts/sync-data.mjs\` first.`,
      { cause },
    );
  }
}

export function readOrgs<T>(): T {
  return read<T>("orgs-nepal-2026.json", join(DIR, "orgs-nepal-2026.json"));
}

export function readDisaster<T>(): T {
  return read<T>("disaster-updates.json", join(DIR, "disaster-updates.json"));
}

export function readDistricts<T>(): T {
  return read<T>("admin2-npl.json", join(DIR, "admin2-npl.json"));
}

export function readDonationChannels<T>(): T {
  return read<T>("donation-channels.json", join(DIR, "donation-channels.json"));
}
