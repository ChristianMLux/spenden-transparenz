import { describe, expect, it } from "vitest";
import { registryDomain } from "./registry-meta";

describe("registryDomain", () => {
  it("returns the known domain for a well-known registry code", () => {
    expect(registryDomain("NP_SWC")).toBe("swc.org.np");
    expect(registryDomain("IATI")).toBe("iatistandard.org");
  });

  it("returns null for a registry with no single well-known domain", () => {
    expect(registryDomain("OTHER")).toBeNull();
    expect(registryDomain("UN")).toBeNull();
  });

  it("returns null for an unrecognised registry code rather than throwing", () => {
    expect(registryDomain("SOMETHING_NEW")).toBeNull();
  });
});
