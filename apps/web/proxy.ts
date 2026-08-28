// Next 16 renamed middleware.ts to proxy.ts. next-intl's factory is unchanged.
//
// The matcher must exclude anything with a dot in it (static files) but nothing else.
// Note the doubled backslash: in a TypeScript string "\." collapses to "." and the
// pattern silently becomes ".*..*", which excludes every path except "/". That failure
// is invisible except that localized pathnames stop resolving.
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  matcher: "/((?!api|_next|_vercel|.*\\..*).*)",
};
