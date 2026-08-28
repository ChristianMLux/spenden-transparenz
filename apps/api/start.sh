#!/usr/bin/env sh
# Production start command (Railway).
#
# --no-server-header: uvicorn, not the app, emits the Server banner. There is no reason to tell
#   the internet which server version is running.
# --proxy-headers with --forwarded-allow-ips: Railway terminates TLS and is the only ingress, so
#   its X-Forwarded-For is the one honest source of the client address. The rate limiter reads the
#   first hop of that header; without these flags every request would look like it came from the
#   proxy and one client could exhaust everyone's budget.
set -eu
exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --no-server-header \
  --proxy-headers \
  --forwarded-allow-ips "*"
