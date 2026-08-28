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
    expect(resolveDistrict("Chitwan district (Mugling)")?.code).toBe("NP0335");
  });

  it("returns null for anything that is not a district, so it becomes 'no location stated'", () => {
    expect(resolveDistrict("unspecified")).toBeNull();
    expect(resolveDistrict("Nepal")).toBeNull();
    expect(resolveDistrict("northern Nepal")).toBeNull();
    expect(resolveDistrict("along the Bhotekoshi and Trishuli rivers")).toBeNull();
    expect(resolveDistrict("unspecified (remote flood-affected areas)")).toBeNull();
  });

  it("never invents a district for an unknown place name", () => {
    expect(resolveDistrict("Somewhere Else")).toBeNull();
  });
});
