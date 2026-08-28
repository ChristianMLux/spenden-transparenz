import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";

// The only non-static route in the application. Everything else is prerendered; this
// handler exists solely so the ingestion pipeline can push a cache invalidation when new
// data lands, without waiting for the next scheduled revalidation window.

const TAG_PATTERN = /^(crisis|org):[a-z0-9-]+$/;

// This was a module-level throw when NODE_ENV was production and the secret was missing.
// It broke `next build`: the build collects page data with NODE_ENV=production and no
// runtime environment, so the whole build failed on a route nobody had called yet. Build
// time is not start time.
//
// The fail-closed behaviour is unchanged, because isAuthorized() already returns false
// without a secret and an unconfigured deployment answers 401 to everything. What was
// lost was the operator signal, so that is logged on the first request instead. Still 401
// rather than a distinct status, deliberately: an unauthenticated caller learns nothing
// about whether the endpoint is configured.
let warnedUnconfigured = false;

function warnIfUnconfigured(): void {
  if (warnedUnconfigured || process.env.REVALIDATE_SECRET) return;
  warnedUnconfigured = true;
  console.error(
    JSON.stringify({
      event: "revalidate.unconfigured",
      message: "REVALIDATE_SECRET is not set. Every revalidation request will be rejected.",
    }),
  );
}

/**
 * Constant-time string comparison. `!==` short-circuits on the first differing byte,
 * which leaks the length of a correct prefix through response timing; `timingSafeEqual`
 * does not, but it throws on unequal-length buffers, so the length check has to happen
 * first (and is not itself timing-sensitive: revealing that a guess had the wrong length
 * gives an attacker nothing about the secret's content).
 */
function safeEqual(a: string, b: string): boolean {
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return timingSafeEqual(bufA, bufB);
}

function isAuthorized(request: Request): boolean {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret) return false;
  const auth = request.headers.get("authorization");
  if (!auth) return false;
  return safeEqual(auth, `Bearer ${secret}`);
}

export async function POST(request: Request): Promise<Response> {
  warnIfUnconfigured();
  if (!isAuthorized(request)) {
    return new Response("unauthorized", { status: 401 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  const tag = body && typeof body === "object" && "tag" in body ? (body as { tag: unknown }).tag : undefined;
  if (typeof tag !== "string" || !TAG_PATTERN.test(tag)) {
    return new Response("bad tag", { status: 400 });
  }

  // Next 16 requires this second argument naming a cacheLife profile; the one-argument
  // form is deprecated and silently does not behave the same way. "hours" matches the
  // profile the loaders in lib/api.ts are cached with.
  revalidateTag(tag, "hours");
  return Response.json({ revalidated: tag });
}
