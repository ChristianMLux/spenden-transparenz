import { readRepoJson } from "./repo-data";
import type { DistrictRef } from "./types";

interface HapiDistrict {
  code: string;
  name: string;
}

// All 77 admin2 districts, so a district that shows up in later data resolves without a
// code change. Codes run country-wide, not per province: Bagmati starts at NP0320, which
// is why the spec's example NP0301 does not exist. Rasuwa is NP0329.
const HAPI = readRepoJson<{ data: HapiDistrict[] }>("data/raw/hapi/admin2_NPL.json").data;

const norm = (s: string) =>
  s
    .toLowerCase()
    .trim()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/\s*\([^)]*\)\s*$/, "")
    .replace(/\s+district$/, "")
    .replace(/\s+/g, " ");

const BY_NAME = new Map<string, DistrictRef>();
for (const d of HAPI) BY_NAME.set(norm(d.name), { code: d.code, name: d.name });

// Settlements and alternative spellings observed in the pilot records. Everything here is
// a place we could point at on a map; ambiguous wording belongs in NOT_A_DISTRICT instead.
const ALIASES: Record<string, string> = {
  timure: "NP0329",
  syabrubesi: "NP0329",
  rasuwagadhi: "NP0329",
  chitwan: "NP0335",
  mugling: "NP0335",
  kathmandu_valley: "NP0327",
};

// Wording that names no district. These become "no location stated", which is a filter
// value of its own and never a silent drop.
const NOT_A_DISTRICT = new Set(["", "unspecified", "nepal", "northern nepal", "central nepal"]);

const BY_CODE = new Map(HAPI.map((d) => [d.code, d.name]));

export function resolveDistrict(raw: string): DistrictRef | null {
  const key = norm(raw);
  if (NOT_A_DISTRICT.has(key)) return null;
  // River corridors and similar spans cross districts; we do not guess which one.
  if (key.startsWith("along ")) return null;

  const direct = BY_NAME.get(key);
  if (direct) return direct;

  const aliased = ALIASES[key.replace(/\s+/g, "_")] ?? ALIASES[key];
  if (aliased) {
    const name = BY_CODE.get(aliased);
    if (name) return { code: aliased, name };
  }
  return null;
}

export function allDistricts(): DistrictRef[] {
  return HAPI.map((d) => ({ code: d.code, name: d.name }));
}
