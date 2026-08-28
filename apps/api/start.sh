#!/usr/bin/env sh
# Production start command (Railway).
#
# --no-server-header: uvicorn, not the app, emits the Server banner. There is no reason to tell
#   the internet which server version is running.
# --proxy-headers with --forwarded-allow-ips: Railway terminates TLS and is the only ingress, so
#   the app needs the forwarded scheme and host to build correct URLs. Without them every request
#   would also look like it came from the proxy.
#
#   Read this before using request.client.host for anything security-relevant. With
#   --forwarded-allow-ips "*", uvicorn takes its always_trust path and sets the client address to
#   the FIRST entry of X-Forwarded-For. That header reads "client, proxy1, proxy2": the client's
#   own value comes first and each proxy appends, so the first entry is whatever the caller chose
#   to send. request.client.host is therefore attacker-controlled here, and anything that keys on
#   it - a rate limit, an audit trail, a per-client budget - is trivially bypassed by rotating it.
#
#   The alternative, naming Railway's proxy addresses instead of "*", is not available: they are
#   internal and dynamic. So the app parses the header itself where it matters. The rate limiter
#   keys on the RIGHTMOST entry (app/deps.py), the one the trusted proxy appended, which is
#   correct whether a proxy appends to the header or replaces it.
set -eu
exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --no-server-header \
  --proxy-headers \
  --forwarded-allow-ips "*"
