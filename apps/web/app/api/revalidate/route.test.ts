import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// revalidateTag() has the same requirement as cacheTag() (see lib/api.test.ts): it needs
// a Next.js server runtime that this Vitest run does not provide. Mocking it lets the
// route handler's own auth/validation logic run for real while keeping the assertion on
// the call itself, which is what proves the second cacheLife argument is actually there.
vi.mock("next/cache", () => ({
  revalidateTag: vi.fn(),
}));

const TEST_SECRET = "a-test-secret-at-least-32-bytes-long-000000";

function request(body: unknown, headers: Record<string, string> = {}): Request {
  return new Request("http://localhost/api/revalidate", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
}

describe("POST /api/revalidate", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env.REVALIDATE_SECRET = TEST_SECRET;
    vi.stubEnv("NODE_ENV", "test");
  });

  afterEach(() => {
    delete process.env.REVALIDATE_SECRET;
    vi.unstubAllEnvs();
  });

  it("returns 401 without an authorization header", async () => {
    const { POST } = await import("./route");
    const res = await POST(request({ tag: "crisis:ff-2026-000162-npl" }));
    expect(res.status).toBe(401);
  });

  it("returns 401 with a wrong secret", async () => {
    const { POST } = await import("./route");
    const res = await POST(
      request({ tag: "crisis:ff-2026-000162-npl" }, { authorization: "Bearer the-wrong-secret" }),
    );
    expect(res.status).toBe(401);
  });

  it("returns 401 when REVALIDATE_SECRET is not configured at all, even with a matching-looking header", async () => {
    delete process.env.REVALIDATE_SECRET;
    vi.resetModules();
    const { POST } = await import("./route");
    const res = await POST(request({ tag: "crisis:ff-2026-000162-npl" }, { authorization: "Bearer undefined" }));
    expect(res.status).toBe(401);
  });

  it("returns 400 on a malformed tag", async () => {
    const { POST } = await import("./route");
    const res = await POST(request({ tag: "not-a-real-tag" }, { authorization: `Bearer ${TEST_SECRET}` }));
    expect(res.status).toBe(400);
  });

  it("returns 400 when the tag field is missing entirely", async () => {
    const { POST } = await import("./route");
    const res = await POST(request({}, { authorization: `Bearer ${TEST_SECRET}` }));
    expect(res.status).toBe(400);
  });

  it("returns 400 on a body that is not valid JSON", async () => {
    const { POST } = await import("./route");
    const res = await POST(
      new Request("http://localhost/api/revalidate", {
        method: "POST",
        headers: { authorization: `Bearer ${TEST_SECRET}` },
        body: "not json",
      }),
    );
    expect(res.status).toBe(400);
  });

  it("returns 200 on a good crisis tag and calls revalidateTag with a cacheLife profile", async () => {
    const { revalidateTag } = await import("next/cache");
    const { POST } = await import("./route");
    const res = await POST(
      request({ tag: "crisis:ff-2026-000162-npl" }, { authorization: `Bearer ${TEST_SECRET}` }),
    );
    expect(res.status).toBe(200);
    // The one-argument form is deprecated in Next 16; this is the assertion that would
    // fail if that form were used instead.
    expect(revalidateTag).toHaveBeenCalledWith("crisis:ff-2026-000162-npl", expect.any(String));
    expect(await res.json()).toEqual({ revalidated: "crisis:ff-2026-000162-npl" });
  });

  it("returns 200 on a good org tag", async () => {
    const { POST } = await import("./route");
    const res = await POST(request({ tag: "org:msf-international" }, { authorization: `Bearer ${TEST_SECRET}` }));
    expect(res.status).toBe(200);
  });

  it("rejects a tag prefix outside crisis/org even if otherwise well-formed", async () => {
    const { POST } = await import("./route");
    const res = await POST(request({ tag: "admin:drop-everything" }, { authorization: `Bearer ${TEST_SECRET}` }));
    expect(res.status).toBe(400);
  });

  it("refuses to load without a configured secret when NODE_ENV is production", async () => {
    delete process.env.REVALIDATE_SECRET;
    vi.stubEnv("NODE_ENV", "production");
    vi.resetModules();
    await expect(import("./route")).rejects.toThrow();
  });

  it("loads fine in production when the secret is configured", async () => {
    process.env.REVALIDATE_SECRET = TEST_SECRET;
    vi.stubEnv("NODE_ENV", "production");
    vi.resetModules();
    await expect(import("./route")).resolves.toBeDefined();
  });
});
