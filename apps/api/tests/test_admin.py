"""POST /v1/admin/ingest/{job}, GET /v1/admin/runs.

No ADMIN_TOKEN is set in this test environment (there is no .env.spenden, and CI does not set
ADMIN_TOKEN for the test job), so every request here is "no token configured" from the server's
point of view. Per app.deps.require_admin_token, that must answer exactly like a wrong token: 401,
never a distinct status, because a distinct status would tell an unauthenticated caller which
deployments forgot to set the token.
"""

from __future__ import annotations

from app.deps import rate_limit_key
from httpx import AsyncClient
from starlette.requests import Request


def _request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("203.0.113.9", 12345),  # an arbitrary fallback address, distinct from any test value
    }
    return Request(scope)


def test_rate_limit_key_uses_the_last_hop_when_there_is_no_proxy_chain():
    """X-Forwarded-For reads left to right as "client, proxy1, proxy2": with a single trusted
    proxy (Railway) directly in front of the app, the LAST entry is the one Railway itself
    appended - the address it actually observed the connection from."""
    key = rate_limit_key(_request_with_headers({"X-Forwarded-For": "9.9.9.9"}))
    assert key == "9.9.9.9"


def test_a_spoofed_first_entry_cannot_change_the_key():
    """The property that matters: a caller cannot dodge the rate limit by prepending a fake
    address of their own choosing. Only Railway's own appended, last entry may set the key."""
    key = rate_limit_key(_request_with_headers({"X-Forwarded-For": "1.2.3.4, 9.9.9.9"}))
    assert key == "9.9.9.9"


def test_rotating_the_spoofed_first_entry_still_yields_the_same_key():
    """The actual attack the rate limit exists to stop: rotating a self-chosen first entry to try
    to get a fresh bucket on every request. It must not work."""
    first = rate_limit_key(_request_with_headers({"X-Forwarded-For": "1.2.3.4, 9.9.9.9"}))
    second = rate_limit_key(_request_with_headers({"X-Forwarded-For": "5.6.7.8, 9.9.9.9"}))
    assert first == second == "9.9.9.9"


def test_rate_limit_key_falls_back_to_the_asgi_client_address_without_the_header():
    key = rate_limit_key(_request_with_headers({}))
    assert key == "203.0.113.9"


async def test_ingest_without_a_token_is_401(client: AsyncClient):
    r = await client.post("/v1/admin/ingest/seed_reference")
    assert r.status_code == 401


async def test_ingest_with_a_wrong_token_is_401(client: AsyncClient):
    r = await client.post("/v1/admin/ingest/seed_reference", headers={"X-Admin-Token": "wrong"})
    assert r.status_code == 401


async def test_runs_without_a_token_is_401(client: AsyncClient):
    r = await client.get("/v1/admin/runs")
    assert r.status_code == 401


async def test_runs_with_a_wrong_token_is_401(client: AsyncClient):
    r = await client.get("/v1/admin/runs", headers={"X-Admin-Token": "wrong"})
    assert r.status_code == 401


async def test_admin_responses_are_never_cached(client: AsyncClient):
    r = await client.post("/v1/admin/ingest/seed_reference")
    assert r.headers["cache-control"] == "no-store"


async def test_admin_ingest_limit_is_five_per_minute_and_counts_failed_auth_attempts(client: AsyncClient):
    """The rate limit must throttle wrong-token attempts too, or brute-forcing the token would
    never trip it. Six rapid requests: the first five are checked against the limit and answer
    401 (wrong token), the sixth is rejected by the limiter itself before the token is even
    compared, answering 429."""
    statuses = []
    for _ in range(6):
        r = await client.post("/v1/admin/ingest/seed_reference", headers={"X-Admin-Token": "wrong"})
        statuses.append(r.status_code)
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429


async def test_ingest_with_a_valid_token_queues_a_run_and_does_not_run_it(client: AsyncClient, monkeypatch):
    """accepted=true means "recorded, and the pipeline will drain it" - not "finished", and not
    even "started". The endpoint writes one ingestion_run row with status="queued" and returns its
    id; nothing pipeline-related runs inside this request. GET /v1/admin/runs is where the queued
    row - and later its outcome - actually shows up."""
    from core.settings import get_settings

    monkeypatch.setenv("ADMIN_TOKEN", "a" * 32)
    get_settings.cache_clear()
    try:
        r = await client.post("/v1/admin/ingest/seed_reference", headers={"X-Admin-Token": "a" * 32})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["accepted"] is True
        assert body["job"] == "seed_reference"
        assert body["run_id"], "a queued run must be a real, retrievable id, not null"

        runs = (await client.get("/v1/admin/runs", headers={"X-Admin-Token": "a" * 32})).json()
        queued = next(run for run in runs if run["id"] == body["run_id"])
        assert queued["status"] == "queued"
        assert queued["job"] == "seed_reference"
        assert queued["rows_written"] == 0
    finally:
        get_settings.cache_clear()


async def test_ingest_with_a_valid_token_but_an_unknown_job_is_404(client: AsyncClient, monkeypatch):
    """The 404 for an unknown job name is checked against core.jobs.JOB_NAMES before anything is
    written, so a typo'd job name never queues a run nothing will ever drain."""
    from core.settings import get_settings

    monkeypatch.setenv("ADMIN_TOKEN", "a" * 32)
    get_settings.cache_clear()
    try:
        r = await client.post("/v1/admin/ingest/does_not_exist", headers={"X-Admin-Token": "a" * 32})
        assert r.status_code == 404
    finally:
        get_settings.cache_clear()
