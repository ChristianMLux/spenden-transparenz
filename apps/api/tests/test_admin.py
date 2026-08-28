"""POST /v1/admin/ingest/{job}, GET /v1/admin/runs.

No ADMIN_TOKEN is set in this test environment (there is no .env.spenden, and CI does not set
ADMIN_TOKEN for the test job), so every request here is "no token configured" from the server's
point of view. Per app.deps.require_admin_token, that must answer exactly like a wrong token: 401,
never a distinct status, because a distinct status would tell an unauthenticated caller which
deployments forgot to set the token.
"""

from __future__ import annotations

from httpx import AsyncClient


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
