import { describe, expect, it } from "vitest";
import { resolveDistrict } from "./districts";

describe("resolveDistrict", () => {
  it("maps a plain district name to its HAPI code", () => {
    expect(resolveDistrict("Rasuwa")).toEqual({ code: "NP0329", name: "Rasuwa" });
  });

  it('maps the "X district" wording used in half the records', () => {
    expect(resolveDistrict("Nuwakot district")).toEqual({ code: "NP0328", name: "Nuwakot" });
    expect(resolveDistrict("Dhading district")?.code).toBe("NP0330");
  });

  it("maps settlements to the district they sit in", () => {
    expect(resolveDistrict("Timure")?.code).toBe("NP0329");
    expect(resolveDistrict("Syabrubesi")?.code).toBe("NP0329");
    expect(resolveDistrict("Rasuwagadhi")?.code).toBe("NP0329");
  });

  it("maps the Chitwan spelling to the HAPI Chitawan code", () => {
    expect(resolveDistrict("Chitwan")?.code).toBe("NP0335");
    expect(resolveDistrict("Chitwan district")?.code).toBe("NP0335");
    expect(resolveDistrict("Chitwan district (Mugling)")?.code).toBe("NP0335");
  });

  // DESIGN.md 12.2: the raw strings measured in orgs-nepal-2026.json. Gorkha and
  // Kavrepalanchok need no alias entry (the "X district" suffix strip plus a direct HAPI
  // name match already resolves them), but they are asserted here so that fact is a test,
  // not something the next reader has to re-derive from the alias table.
  it("resolves Gorkha and Kavrepalanchok by name, no alias entry required", () => {
    expect(resolveDistrict("Gorkha")?.code).toBe("NP0436");
    expect(resolveDistrict("Gorkha district")?.code).toBe("NP0436");
    expect(resolveDistrict("Kavrepalanchok")?.code).toBe("NP0324");
  });

  it("returns null for anything that is not a district, so it becomes 'no location stated'", () => {
    expect(resolveDistrict("unspecified")).toBeNull();
    expect(resolveDistrict("Nepal")).toBeNull();
    expect(resolveDistrict("northern Nepal")).toBeNull();
    expect(resolveDistrict("along the Bhotekoshi and Trishuli rivers")).toBeNull();
    // The second, differently-spelled river formulation observed in the pilot data.
    expect(resolveDistrict("along Bhote Koshi and Trishuli rivers")).toBeNull();
    expect(resolveDistrict("unspecified (remote flood-affected areas)")).toBeNull();
  });

  it("never invents a district for an unknown place name", () => {
    expect(resolveDistrict("Somewhere Else")).toBeNull();
  });
});
