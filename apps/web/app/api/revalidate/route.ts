import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";

// The only non-static route in the application. Everything else is prerendered; this
// handler exists solely so the ingestion pipeline can push a cache invalidation when new
// data lands, without waiting for the next scheduled revalidation window.

const TAG_PATTERN = /^(crisis|org):[a-z0-9-]+$/;

// Refuse to start without the secret in production, rather than silently accepting
// requests nobody can ever authorize (a wrong-looking failure) or, worse, accepting
// every request because the auth check below degrades open. This runs once, when the
// module is first loaded by the running server.
if (process.env.NODE_ENV === "production" && !process.env.REVALIDATE_SECRET) {
  throw new Error("REVALIDATE_SECRET must be set in production. Refusing to start this route.");
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
