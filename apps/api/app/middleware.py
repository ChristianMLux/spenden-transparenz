"""ETag middleware.

Hashes the serialised response body and answers 304 with an empty body when the caller's
If-None-Match already matches. GET only: writes never have a meaningful ETag, and neither do
error responses, so both are passed through untouched.

Buffering the body here is deliberate: this API is JSON only and every response is small (a
disaster board is at most 100 rows), so reading the streamed body into memory once per request
costs nothing measurable and is the only way to hash it. Starlette's own BaseHTTPMiddleware works
exactly this way internally - see body_stream() in starlette/middleware/base.py.
"""

from __future__ import annotations

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class ETagMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if request.method != "GET" or response.status_code != 200:
            return response
        if response.headers.get("cache-control") == "no-store":
            # no-store already tells the caller never to reuse this response; an ETag on top of
            # that would be a contradiction, not an optimisation.
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
        etag = f'"{hashlib.sha256(body).hexdigest()}"'

        if request.headers.get("if-none-match") == etag:
            headers = dict(response.headers)
            headers["etag"] = etag
            headers.pop("content-length", None)
            return Response(status_code=304, headers=headers)

        headers = dict(response.headers)
        headers["etag"] = etag
        return Response(content=body, status_code=response.status_code, headers=headers)
