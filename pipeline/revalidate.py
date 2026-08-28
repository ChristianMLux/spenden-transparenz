"""Tell the web app that a cached page is stale.

Best-effort by construction. A revalidation is a cache hint, not data: the rows are already
committed by the time this runs, and a web app that is down, slow or misconfigured must never turn
a successful ingestion into a failed one. Every failure path here logs and returns.

Contract (web team, 2026-08-28):
    POST {WEB_BASE_URL}/api/revalidate
    Authorization: Bearer {REVALIDATE_SECRET}
    {"tag": "crisis:ff-2026-000162-npl"}    one tag per request
    200 {"revalidated": tag} · 401 unconfigured or wrong secret · 400 bad JSON or bad tag

Tags are `crisis:<glide_id>` after any run that wrote statements, reports or districts, and
`org:<org_id>` per organisation whose datums changed.

Until the web build has SPENDEN_API_URL it re-renders from baked JSON, so this is a visible no-op
before PO-5. It is wired now so the wiring is not the thing that breaks on deploy day.
"""

from __future__ import annotations

import re

import requests
from core.logging import get_logger
from core.settings import Settings, get_settings

log = get_logger("revalidate")

# The web app validates this too; matching it here means a bad tag is caught before a request
# leaves the machine, and the log names the tag rather than an opaque 400.
TAG_PATTERN = re.compile(r"^(crisis|org):[a-z0-9-]+$")

TIMEOUT_SECONDS = 10


def crisis_tag(glide_id: str) -> str:
    return f"crisis:{glide_id}"


def org_tag(org_id: str) -> str:
    return f"org:{org_id}"


def revalidate(tags: list[str], settings: Settings | None = None) -> int:
    """Ask the web app to revalidate each tag. Returns how many it accepted.

    Never raises. A cache hint that fails is worth a log line, not a failed ingestion run.
    """
    settings = settings or get_settings()

    if not settings.web_base_url or settings.revalidate_secret is None:
        log.info("revalidate_skipped_not_configured", extra={"tags": len(tags)})
        return 0

    unique = list(dict.fromkeys(tags))
    valid = [tag for tag in unique if TAG_PATTERN.match(tag)]
    for tag in unique:
        if tag not in valid:
            log.warning("revalidate_tag_rejected_locally", extra={"tag": tag})

    if not valid:
        return 0

    url = f"{settings.web_base_url.rstrip('/')}/api/revalidate"
    headers = {"Authorization": f"Bearer {settings.revalidate_secret.get_secret_value()}"}

    accepted = 0
    # One request per tag: the contract takes one tag, and a batch endpoint that half-succeeded
    # would be harder to report on than n small calls.
    with requests.Session() as session:
        for tag in valid:
            try:
                response = session.post(url, json={"tag": tag}, headers=headers, timeout=TIMEOUT_SECONDS)
            except requests.RequestException as exc:
                log.warning("revalidate_request_failed", extra={"tag": tag, "error_type": type(exc).__name__})
                continue
            if response.status_code == 200:
                accepted += 1
            else:
                # 401 is deliberately indistinguishable between "unconfigured" and "wrong secret",
                # so the log says what we saw and does not speculate about which.
                log.warning("revalidate_rejected", extra={"tag": tag, "status": response.status_code})

    log.info("revalidate_done", extra={"requested": len(valid), "accepted": accepted})
    return accepted
