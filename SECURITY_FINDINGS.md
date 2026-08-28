# Security Findings - spenden-transparenz v1, Gate PO-4

Reviewer: security-reviewer (opus). Branch `review/security-po4` off `origin/main` at
`35100da`. Skills loaded before review: `app-reviewer` (anti-patterns.md),
`security-hardening` (references/fastapi.md), `performance-spotter`.

## Verdict

**Fix first.** The architecture is sound and the hard parts are right: the SQL layer is fully
parameterised, `body_text` never leaves the database, input validation is genuinely tight, the
admin endpoint really does only queue, and the API image really does not import the pipeline. The
four blocking findings are all narrow and all cheap to fix, but three of them make a control that
the spec's checklist requires *not actually exist* in the shipped artefact rather than merely being
weak: there is no rate limit on any GET route at all, the admin rate-limit key is still
attacker-controlled through a header shape nobody tested, and a plausible operator-chosen
`ADMIN_TOKEN` bricks the admin endpoint with a 500. The fourth is the trustee data, which was
removed from the working tree but is still served by GitHub from this public repository's history.
None of these are architectural. All four should be fixable well inside a single sitting, and the
485-test suite already passing means there is a net underneath the changes.

Evidence for every claim below was produced by running the code, not by reading it. Probe scripts
were written into `apps/api/tests/`, executed, and deleted; the working tree is clean.

---

## Resolution (backend lead, 2026-08-28)

Recorded after the review, against the findings as written. Nothing above was edited to match an
outcome; the review stands as it was filed.

| | finding | outcome |
|---|---|---|
| B1 | no rate limit on any GET route | **fixed** in PR #31 - and the cause was larger than the finding, see below |
| B2 | rate-limit key defeated by a repeated `X-Forwarded-For` header | **fixed** in PR #31 |
| B3 | non-ASCII `ADMIN_TOKEN` bricks the admin endpoint | **fixed** in PR #31 |
| B4 | trustee names in the public repository's history | **risk accepted by the owner** - no rewrite |
| N1 | nothing drains queued ingestion runs | **fixed** - the lead ruled it v1 |

**B1 was worse than reported, and the reported fix would not have worked.** Setting the Limiter's
`default_limits` changes nothing here: `SlowAPIMiddleware` resolves the handler through
`route.matches(scope)` plus `hasattr(route, "endpoint")`, and this FastAPI version wraps an
included router in an `_IncludedRouter` object that matches `Match.FULL` and carries no `endpoint`
attribute. slowapi therefore finds no handler, and `_should_exempt` treats a `None` handler as
**exempt** - so the middleware was passing every request through untouched. Measured with
`default_limits` set: 61 consecutive GETs to `/v1/meta/enums`, all 200. The admin limit worked only
because a route decorator is checked inside the endpoint and never went through the middleware.

A middleware that announces a rate limit it cannot enforce is worse than no middleware, so it was
removed. The read limit is a dependency applied to the v1 routers at include time, over the same
Limiter and therefore the same storage. `/health` is deliberately outside it: Railway polls it,
every request through Railway shares one rate-limit key, and 429ing the healthcheck would restart a
healthy container - the rate limit taking the service down instead of protecting it.

The `.isascii()` start-up restriction suggested for B3 was **not** added. Comparing bytes makes a
non-ASCII token work correctly rather than crash, so refusing one at start-up would have been a new
defect rather than a guard.

The query-amplification half of B1 (`list_orgs` calling `_detail()` per row) is **not** fixed and
is not tracked here as security - with the rate limit now real, the amplification is bounded. It
belongs with the performance work.

---

## The 8-point checklist

### 1. Admin token - PASS WITH NOTE

`secrets.compare_digest` is used (`apps/api/app/deps.py:98`), there is no default value
(`packages/core/core/settings.py:42`, `admin_token: SecretStr | None = None`), production refuses
to start without one and enforces >= 32 bytes (`settings.py:76-86`), and the unconfigured-token
branch returns **401, never 503** - `expected` becomes `""` and the `or not expected` clause forces
the 401 after `compare_digest` has already run on both paths, so neither the status code nor the
timing reveals that no token is set.

Verified live - the only non-GET route in the entire API, called without a token:

```
PROBE admin POST no token -> 401 {"detail":"invalid admin token"}
  headers: {'cache-control': 'no-store', 'content-type': 'application/json',
            'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer',
            'x-frame-options': 'DENY'}
```

Full route inventory from `apps/api/openapi.json` confirms one write route, and it is the guarded
one:

```
POST   /v1/admin/ingest/{job}      <- require_admin_token
GET    /v1/admin/runs              <- require_admin_token
GET    /health, /health/ready, /v1/disasters..., /v1/orgs..., /v1/statements, /v1/meta/...
```

The note is **B3**: a non-ASCII token, which the start-up validator accepts, turns every admin
request into a 500.

### 2. SSRF - PASS

`is_allowed_host` (`pipeline/jobs/reliefweb.py:75-89`) parses the URL and compares the **hostname**,
exact or dot-prefixed suffix - never a substring of the raw URL. It closes the
`reliefweb.int.evil.example` lookalike hole explicitly, and it rejects a URL with no hostname
(`file://`, and `http://reliefweb.int@evil.com/` parses to hostname `evil.com` and is rejected).
The allowlist is applied **before** the per-run budget (`reliefweb.py:77-78`), so an off-allowlist
row cannot even consume a fetch slot. Default hosts are `("reliefweb.int", "api.reliefweb.int")`
(`settings.py:67`).

`validate_orgs.spotcheck()` is CLI-only as required: it lives in `pipeline/probes/validate_orgs.py`,
is reachable only through `main()` under `if __name__ == "__main__"` and the
`scripts/validate_orgs.py` shim. It is not in `JOB_NAMES` (`packages/core/core/jobs.py:21-29`) and
not in the `JOBS` registry (`pipeline/cli.py:33-41`), so it cannot be reached over HTTP through the
admin endpoint. Confirmed by grep: nothing under `apps/api/` imports it.

Residual, non-blocking: `spotcheck()` itself fetches arbitrary `source_url` values with no
allowlist, and `pipeline/probes/common.py:27-34` builds a `requests.Session` that follows redirects.
That is acceptable for an operator-run research script and is noted as **N8**, not as an SSRF sink.

### 3. body_text leak - PASS

The column exists (`packages/core/core/models.py:333`) and is documented as never-served
(`models.py:319`). Grepped every response model and every router: `body_text` appears in
`apps/api/` only in `app/schemas.py:8` as a comment explaining the rule and in the migration that
creates the column. It appears in no `*Out` model and in no router.

Verified live against the seeded contract database, over the three endpoints that serve statement
text:

```
PROBE body_text absent from all list responses: OK
  (/v1/orgs?limit=100, /v1/statements?limit=100,
   /v1/disasters/ff-2026-000162-npl/responders?limit=100)
PROBE /openapi.json -> 200   body_text present: False
```

CI also guards the published contract (`.github/workflows/ci.yml:104-110`).

### 4. SQL - PASS

Every filter is SQLAlchemy Core with bound parameters; there is no f-string SQL anywhere in
`apps/api/`. `q` goes through `ilike_pattern()` (`deps.py:38-47`), which escapes the escape
character first and then `%` and `_`, and is passed with an explicit `escape=` argument
(`orgs.py:80`, `responders.py:179,218-219`). `sort` is a `Literal` (`orgs.py:31`,
`responders.py:57`), so no ORDER BY is ever built from a caller string.

`ruff check .` with `select = ["E","F","I","B","UP","S","ASYNC","RUF"]` (`ruff.toml:10`) - S608 is
in that set - passes:

```
=== ruff check ===
All checks passed!
```

Verified live that the escaping is correct rather than merely present. A bare `%` returns zero
rows, not every row, which is the correctness half of the same bug:

```
PROBE q='%'                                 -> 200 rows=0
PROBE q='_'                                 -> 200 rows=0
PROBE q="' OR 1=1 --"                       -> 200 rows=0
PROBE q="a'; DROP TABLE organisations; --"  -> 200 rows=0
PROBE q='\\'                                -> 200 rows=0
PROBE sort injection ("name; DROP TABLE x") -> 422 literal_error
```

### 5. Rate limit - FAIL

Two independent failures, **B1** and **B2**.

The 5/min admin limit exists and fires (`admin.py:48,78`), and putting the token check inside the
function body so the limiter runs first is the right call:

```
PROBE 12x GET /v1/admin/runs (wrong token) ->
  [401, 401, 401, 401, 401, 429, 429, 429, 429, 429, 429, 429]
```

But **the 60/min GET limit does not exist**. `GET_LIMIT = "60/minute"` (`deps.py:124`) is defined
and never referenced; `SlowAPIMiddleware` (`main.py:104`) only enforces the limiter's
`default_limits`, and the limiter is constructed without any (`deps.py:122`):

```
PROBE limiter default_limits: []
PROBE limiter route_limits keys: ['app.routers.admin.list_runs', 'app.routers.admin.trigger_ingest']
PROBE 80x GET /v1/meta/enums  -> {200: 80}
PROBE 80x GET /v1/disasters   -> {200: 80}
```

And the key function is still attacker-controlled, for a different reason than the one that was
already fixed. See **B1**, **B2**.

Railway's proxy being trusted is documented (`start.sh:6-20`, `deps.py:104-112`) and the reasoning
about the rightmost entry is correct as far as it goes - see the assessment of the lead's finding
(a) below.

### 6. CORS - PASS

`allow_origins=settings.cors_origins` with a validator that rejects `"*"` at construction time
(`settings.py:69-74`), `allow_methods=["GET","OPTIONS"]`, `allow_headers=["X-Admin-Token"]`
(`main.py:93-101`). A wildcard cannot be configured even by mistake. Verified that an unlisted
origin gets no ACAO header rather than a permissive one:

```
PROBE CORS evil origin -> 200  acao: None
```

Non-blocking ergonomics notes at **N6**.

### 7. No natural persons - FAIL

The working tree is clean and the path is gitignored (`.gitignore:6`):

```
$ ls data/raw/ukcc_api/ | grep -i trustee
NONE in working tree
```

**But the files are still in this public repository's history, and history is what GitHub serves.**
Both commits that carry them are ancestors of `origin/main`:

```
$ git log --all --oneline -- 'data/raw/ukcc_api/charitytrusteeinformation_*.json'
5266c6c Step 0: v1 design spec, agent conventions, drop trustee-name files
f081415 Research phase: data-source feasibility, Nepal 2026 pilot dataset, case studies

$ git merge-base --is-ancestor f081415 origin/main && echo yes
f081415 IS ancestor of origin/main
585b925 IS ancestor of origin/main

$ git show f081415:data/raw/ukcc_api/charitytrusteeinformation_1047178.json | head
{ "retrieved_at": "2026-08-28T12:59:37+00:00", "source": "ukcc_api", "data": [
  { "name": "DIANE NORTON", "is_chair": false,
    "date_of_appointment": "2025-10-04T00:00:00", ...
```

Counted across the seven files at that commit: **52 named natural persons**, each with an
appointment date and a charity affiliation. See **B4**.

Separately: the CI gate that is supposed to enforce this checks only the current index
(`.github/workflows/ci.yml:119`, `git ls-files | grep -i charitytrusteeinformation`), so it passes
today and would keep passing forever with the data still published.

### 8. Secrets and headers - PASS WITH NOTE

gitleaks, run exactly as the house rules specify:

```
$ MSYS_NO_PATHCONV=1 docker run --rm -v "C:/.../st-wt-sec-review:/repo" \
    zricethezav/gitleaks:latest detect -s /repo --no-git --no-banner --redact
INF scanned ~4089097 bytes (4.09 MB) in 1.46s
INF no leaks found
```

pip-audit, from the full local suite: `No known vulnerabilities found`. Both also run in CI
(`ci.yml:88-102`), with gitleaks at `fetch-depth: 0` so it covers history.

Secrets come only from the environment or `./.env.spenden` (`settings.py:20-34`), `.env*` is
gitignored, and `SecretStr` is used for all four secrets. Response headers are correct on every
path tested, including 404 and 401:

```
PROBE 200 headers: {'cache-control': 'public, max-age=60, stale-while-revalidate=600',
  'x-total-count': '4', 'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer',
  'x-frame-options': 'DENY', 'etag': '"1294de4c...e45a"'}
PROBE 404 headers: {'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer',
  'x-frame-options': 'DENY'}
```

No `Server` banner: `start.sh:25` passes `--no-server-header`, and no ASGI response sets one.
`/docs` and `/openapi.json` are public on purpose (`main.py:83-85`) and confirmed 200 - correct for
an open-data API.

Notes: the log redaction list omits two of the four secrets (**N3**), and `.env.example` documents
only the four research keys, not `ADMIN_TOKEN` / `DATABASE_URL` / `OPENROUTER_API_KEY` /
`REVALIDATE_SECRET`, which is how a required variable gets forgotten at deploy time (**N9**).

---

## The two findings the backend lead brought in

### (a) `--forwarded-allow-ips "*"` makes `request.client.host` attacker-controlled

**The reasoning is correct.** Confirmed against the installed uvicorn 0.52.4 rather than from
memory - `.venv/Lib/site-packages/uvicorn/middleware/proxy_headers.py`:

```
109:  self.always_trust: bool = trusted_hosts in ("*", ["*"])
176:  if self.always_trust:
177:      return _parse_host_port(x_forwarded_for_hosts[0])     # leftmost, client-chosen
```

Line 180 shows the non-wildcard path walking `reversed(...)` instead, which is what makes the
difference. So with `start.sh:27`, `request.client.host` on this deployment is whatever the caller
put first in `X-Forwarded-For`.

**Nothing reads it today.** Grepped the whole repository: the only occurrence outside comments and
tests is `deps.py:119`, the fallback branch of `rate_limit_key`, reached only when there is no
`X-Forwarded-For` header at all. Behind Railway that branch does not fire for external traffic, and
if it ever did it would return Railway's own address - every caller sharing one bucket, which
over-limits rather than under-limits. Fail-shut, so acceptable.

**The mitigation is adequate in its intent but not in its implementation**, and the gap is not the
one the comment anticipates. See **B2**: the header is read in a way that a caller can steer.

The conclusion that naming Railway's proxy IPs is not possible is right, and the chosen strategy -
parse the header in the app, key on the rightmost entry - is the correct one. It just has to parse
the header the way the HTTP spec defines it.

### (b) The admin endpoint queues and the API must not import the pipeline

**The boundary holds.** Verified by grep across `apps/api/`: no `import pipeline`, no
`from pipeline...`, nothing. The shared vocabulary is `packages/core/core/jobs.py`, which contains
only a tuple of names. `admin.py:60` inserts one row with `status="queued"` and returns; nothing
long-running happens inside the request.

**An unauthenticated party cannot influence what gets queued.** The token check runs before any
write (`admin.py:55`), the job name is validated against `JOB_NAMES` before the insert
(`admin.py:57-58`), and `job` is the only caller-supplied value that reaches the row - `status` is a
literal and every counter defaults server-side. There is no request body. An unknown job name gets
404 after the token check, so it is not an unauthenticated enumeration oracle either.

**But nothing drains the queue.** This is the part to act on. Grepped the entire pipeline package
for the queued status: the only occurrences are comments and tests. `pipeline/runs.py:81` only ever
creates runs with `status="running"`; there is no code path anywhere that selects
`status == "queued"` and executes it. Four separate docstrings assert that the drain exists
(`admin.py:19`, `jobs.py:9`, `enums.py:105`, migration `0003:43`). See **N1** - not a
vulnerability, but the admin endpoint will answer `{"accepted": true}` in production while doing
nothing, and PO-5 should not be signed off believing otherwise.

---

## Blocking

Four findings. All must be fixed before PO-5.

### B1. No rate limit on any GET route, and the org list endpoint is a query amplifier

- **Where:** `apps/api/app/deps.py:124` (`GET_LIMIT` defined, never referenced),
  `apps/api/app/main.py:102-104` (limiter registered with no `default_limits`),
  `apps/api/app/routers/orgs.py:95` (the amplifier).
- **Evidence:** 80 consecutive GETs to `/v1/meta/enums` and to `/v1/disasters` all returned 200;
  `limiter._default_limits` is `[]` and `_route_limits` covers only the two admin routes. Query
  counting via a SQLAlchemy `before_cursor_execute` listener on a 4-organisation seed:
  `GET /v1/orgs?limit=50 -> 17 queries`, `GET .../responders?limit=50 -> 4 queries`.
- **Why it matters here:** checklist item 5 requires 60/min on GET and the control is simply absent.
  It matters more than a missing-header finding because `list_orgs` calls `_detail()` once per row
  (`orgs.py:95`) and `_detail()` issues four queries per organisation (`orgs.py:99-108`), so cost is
  `1 + 4N`. 17 queries for 4 orgs measured; with the real 44-organisation dataset and `limit=100`
  that is roughly 177 database round trips for one unauthenticated HTTP request, against a Railway
  hobby Postgres. One machine can saturate the database of a public-interest site that is most
  valuable precisely when a disaster puts it in front of journalists. The responders board - the
  page that is the product - is correctly built at 4 queries and shows the intended shape.
- **Fix:** two parts, both small.
  1. Apply the limit. Add `@limiter.limit(GET_LIMIT)` to the GET routes (each needs `request:
     Request` in its signature), or simpler and uniform: construct the limiter with
     `Limiter(key_func=rate_limit_key, default_limits=[GET_LIMIT])` so `SlowAPIMiddleware` covers
     every route, and keep the stricter per-route `ADMIN_LIMIT` decorators - slowapi applies the
     route limit in addition to the default. Assert it with a test that walks one endpoint past 60.
  2. Kill the amplifier. `list_orgs` should batch the four per-organisation lookups the way
     `hydrate_statements` already does for statements (`statements.py:99-116`): fetch aliases,
     registrations, warnings and datums for the whole page in four `IN (...)` queries and group in
     Python, giving a flat 5 queries regardless of page size. That helper is the pattern to copy;
     it is in the codebase already.

### B2. The rate-limit key is defeated by a repeated `X-Forwarded-For` header

- **Where:** `apps/api/app/deps.py:116` - `request.headers.get("x-forwarded-for")`.
- **Evidence:** Starlette's `Headers.get` returns only the **first** occurrence of a header name.
  `X-Forwarded-For` is a list header and RFC 7230 s3.2.2 makes `A: 1` / `A: 2` on two lines exactly
  equivalent to `A: 1, 2` - so `.split(",")[-1]` reads the last element of the *first line*, not the
  last element of the list. Probe against the real function:

  ```
  merged single line   ("1.2.3.4, 203.0.113.9")               -> 203.0.113.9   (correct)
  two header lines     ("1.2.3.4" / "203.0.113.9")            -> 1.2.3.4       (caller's value)
  rotated, two lines   ("1.1.1.1" / ...) vs ("2.2.2.2" / ...) -> 1.1.1.1 vs 2.2.2.2
  uvicorn, same input, merges first                           -> '1.2.3.4, 203.0.113.9'
  ```

  uvicorn's own middleware collects **all** `x-forwarded-for` values and joins them before parsing
  (`proxy_headers.py:37-54`). This code does not.
- **Why it matters here:** it reintroduces exactly the bypass the rightmost-entry fix was written to
  close, and the comment at `deps.py:107-112` explicitly claims immunity to it - "correct whether
  Railway appends to an existing header or replaces it outright". That enumeration is missing the
  third case, a proxy that adds its own header line, and the caller is the one who decides whether
  more than one line exists. If Railway appends a line rather than extending one, an attacker gets a
  fresh bucket per request by rotating their own line and brute-forces the 5/min admin token limit
  freely. I could not verify Railway's exact emission behaviour from here and am not going to guess
  it - but the one-line fix makes the question moot, which is better than an answer that depends on
  a vendor's undocumented internals.
- **Fix:** parse the header list the way uvicorn does.

  ```python
  def rate_limit_key(request: Request) -> str:
      forwarded = request.headers.getlist("x-forwarded-for")
      if forwarded:
          return ", ".join(forwarded).split(",")[-1].strip()
      return request.client.host if request.client else "unknown"
  ```

  Then extend `apps/api/tests/test_admin.py:27-46`, which currently only covers the single-line
  cases, with a repeated-header case - it is the case that fails today.

### B3. A non-ASCII `ADMIN_TOKEN` passes start-up validation and then 500s every admin request

- **Where:** `apps/api/app/deps.py:98` (`secrets.compare_digest` on `str`),
  `packages/core/core/settings.py:84` (the length check counts bytes, not ASCII).
- **Evidence:** `secrets.compare_digest` refuses non-ASCII `str` inputs. Probed end to end:

  ```
  token = "korrektur-uebersicht-spenden-schluessel-fuer-pruefung-<umlauts>"
  token bytes: 60 | ascii? False
  Settings(env="production", ...) ACCEPTED it       (>= 32 bytes passes; there is no ASCII check)
    require_admin_token with the CORRECT token -> RAISED TypeError:
      comparing strings with non-ASCII characters is not supported   (=> HTTP 500, not 401)
    require_admin_token with a wrong token     -> RAISED TypeError  (=> HTTP 500, not 401)
    require_admin_token with empty             -> RAISED TypeError  (=> HTTP 500, not 401)
  ```

  The caller-side variant is reachable against a perfectly normal ASCII token too - one non-ASCII
  byte in the header is enough, and over HTTP it surfaces as `UnicodeEncodeError` because Starlette
  decodes headers as latin-1:

  ```
  PROBE non-ASCII X-Admin-Token -> RAISED UnicodeEncodeError:
    'ascii' codec can't encode character '\xf6' in position 1
  ```
- **Why it matters here:** two distinct failures from one line. The operator-facing one is the
  worse: this is a German-language project whose operator may well generate a passphrase-style
  token, the production validator accepts it, the service starts clean, and then **the correct token
  is rejected with a 500** - the admin endpoint is bricked with no start-up signal and a symptom
  that points nowhere near the cause. The attacker-facing one falsifies the invariant
  `deps.py:83-84` states in its own docstring ("Always 401, never a distinct status"): any
  unauthenticated caller can turn the auth path into an unhandled 500 with one header byte. Neither
  is an auth bypass - I want to be precise about that - but an unhandled exception in the one
  function that guards the only write route is not something to carry through a deploy gate when the
  fix is two lines.
- **Fix:** compare bytes, which has no ASCII restriction, and reject a non-ASCII token at start-up
  so the operator learns immediately rather than at 3am.

  ```python
  # deps.py
  configured = get_settings().admin_token
  expected = configured.get_secret_value().encode("utf-8") if configured is not None else b""
  presented = (x_admin_token or "").encode("utf-8", errors="replace")
  if not secrets.compare_digest(presented, expected) or not expected:
      raise HTTPException(401, "invalid admin token", headers={"Cache-Control": NO_STORE})
  ```

  and in `settings.py:84`, alongside the length check, require `.isascii()` with a message that says
  why. Add a test for a non-ASCII header against an ASCII token asserting 401, and a settings test
  asserting a non-ASCII token is refused in production.

### B4. 52 trustee names are still published in the public repository's git history

> **CLOSED - risk accepted by the repository owner, 2026-08-28.** No history rewrite. The
> rationale: UK Charity Commission trustee data is a *public register*, published by the Commission
> under the Open Government Licence v3.0, so republication is licensed rather than a disclosure of
> anything the Commission has not already published itself. The files are out of the working tree
> and gitignored, the probe that fetched them never persists trustee records, and the CI guard
> prevents re-introduction. The finding below stands as written and is left unedited on purpose -
> the analysis was correct, and the decision was made against it with the facts in view, which is
> the record worth keeping. What changed is the accepted risk, not the assessment.
>
> Residual risk, stated plainly rather than argued away: the seven files remain reachable by SHA at
> `f081415` and `585b925` for anyone who clones. The OGL covers the licensing question, not the
> GDPR one - a public register does not make a German operator's republication of it automatically
> lawful under Art. 6, and a trustee's erasure request under Art. 17 could not be satisfied without
> the rewrite this decision declines. If a Datenschutz page is later written that claims no natural
> persons are processed, that claim and this decision cannot both stand; revisit then.
>
> Guard as it stands: `git ls-files` check in CI, `.gitignore`, and a probe that never persists.
> The CI gate's limitation noted in fix step 3 below is real - it tests HEAD, not history - but with
> no purge planned there is nothing for a history check to enforce beyond what the ls-files gate
> already prevents.


- **Where:** commits `f081415` and `585b925`, both ancestors of `origin/main`; seven files under
  `data/raw/ukcc_api/charitytrusteeinformation_*.json`. Ineffective guard at
  `.github/workflows/ci.yml:119`.
- **Evidence:** counts per file at `f081415` - 7, 1, 10, 4, 11, 14, 5 = **52 named natural persons**,
  each with `name`, `date_of_appointment` and charity affiliation. `git merge-base --is-ancestor`
  confirms both commits are reachable from `origin/main`, so `git clone` retrieves them and GitHub
  serves them at those SHAs today.
- **Why it matters here:** checklist item 7 is not a hygiene rule for this product, it is the
  product's own claim. The spec's Phase 0 says the files "werden aus dem oeffentlichen Repo
  entfernt", the API description says the service does not rate or rank organisations, and the whole
  trust proposition rests on the operator being careful with data about people. Deleting from HEAD
  is not removing from a public repository. These are UK Charity Commission trustees - identifiable
  living individuals, GDPR Art. 4(1) personal data, published by a German operator with an Impressum
  and a Datenschutz page that will describe what this project processes. The delta between "we do
  not ingest natural persons" and a `git log -p` away is exactly the kind of gap that costs a
  transparency project its credibility, and it is the one finding here that a journalist could find
  without reading code.
- **Fix (not taken - see the decision above):** rewrite the history and force-push, then close the hole that let CI bless it.
  1. `git filter-repo --path-glob 'data/raw/ukcc_api/charitytrusteeinformation_*.json' --invert-paths`
     (or BFG), on a fresh mirror clone, then force-push `main`. The repository is young, public and
     has no external contributors, so a rewrite is cheap now and only gets more expensive.
  2. Ask GitHub Support to purge the cached blobs; a rewrite alone leaves them reachable by SHA
     until GitHub garbage-collects, and forks/caches will not follow.
  3. Change `ci.yml:119` from `git ls-files` to a history check, so the gate actually tests the
     claim it is named after:
     `git log --all --diff-filter=A --name-only --pretty=format: | grep -i charitytrusteeinformation`
  4. Coordinate the force-push with the other worktrees on this repo before doing it.

---

## Non-blocking

Ordered by how much they will cost if left. **N1 is not a security issue but is a functional
blocker for the admin feature** - the lead should decide whether PO-5 ships with it.

### N1. Nothing drains queued ingestion runs

> **FIXED 2026-08-28.** The lead's ruling: an admin endpoint that answers `accepted` and does
> nothing is a lie in the API, so the drain is v1, not post-v1. `pipeline/queue.py` claims the
> oldest queued run with `FOR UPDATE SKIP LOCKED`, marks it running, dispatches it through the
> `JOBS` registry, and closes the row with its result; `pipeline/runs.py` grew `adopt_run` so the
> job reports into the queued row rather than opening a second one beside it. Exposed as
> `python -m pipeline.cli drain`, which is what the Railway cron calls. Nine tests in
> `pipeline/tests/test_queue.py`, including the two this finding names: only `queued` rows are ever
> claimed, and one failing job does not strand the runs queued behind it.


`apps/api/app/routers/admin.py:60` writes `status="queued"`; `pipeline/runs.py:81` only ever writes
`status="running"`. Grepping the pipeline package for the queued status returns comments and tests
only - there is no consumer. Four docstrings assert a drain exists (`admin.py:19`, `jobs.py:9`,
`enums.py:105`, migration `0003:43`) and `pipeline/tests/test_job_registry.py` guards the
name-registry agreement, which reads as coverage of this but is not. **Fix:** add a `drain_queued`
step at the start of the pipeline tick that selects `status == "queued"` oldest-first, marks each
`running` (with `SELECT ... FOR UPDATE SKIP LOCKED` so two ticks cannot take the same row), and
dispatches through the existing `JOBS` registry; or, if that is post-v1, make the endpoint say so -
returning `accepted: true` for work nothing will do is the kind of true-looking claim this project
exists to argue against.

### N2. The middleware-order comment states the opposite of the actual order

`apps/api/app/main.py:89-91` says "(outermost first) security headers -> ETag -> CORS -> rate
limiting". Starlette's `add_middleware` does `user_middleware.insert(0, ...)`, so the last one added
is outermost. Measured: `['SlowAPIMiddleware', 'CORSMiddleware', 'ETagMiddleware',
'SecurityHeadersMiddleware']`, outermost first - exactly reversed. Consequences are mild today
(`ExceptionMiddleware` sits inside `SecurityHeadersMiddleware`, so 401s and 429s do get the headers,
which the probes confirm; only a `ServerErrorMiddleware` 500 misses them). But this comment exists
to stop the next person reordering things wrongly, and it will do the opposite. **Fix:** correct the
comment, and if the intent was for security headers to be outermost, add that middleware last.

### N3. The log redaction list covers two of the four secrets

`apps/api/app/main.py:57` and `pipeline/cli.py:63` both pass only `admin_token` and
`openrouter_api_key` to `configure_logging`. `revalidate_secret` (`settings.py:64`) and the password
inside `database_url` are not registered, so `_RedactingFormatter` will not strip them from a
traceback or a stray `extra=`. The codebase already treats this as a live risk - `health.py:38`
says "The exception text can contain the DSN with its password" and works around it locally.
**Fix:** add `revalidate_secret` to both lists, and parse the password out of `database_url`
(`sqlalchemy.engine.make_url(...).password`) and register it too. Both are one-liners in a function
that already does the hard part.

### N4. `alembic downgrade` from 0003 silently deletes hand-researched statements

`apps/api/alembic/versions/0003_queued_runs_and_hand_researched_.py:77` -
`op.execute("DELETE FROM response_statement WHERE quote IS NULL")`. The comment two lines above
says "Dropping them is not this migration's call to make silently", and then the code does it
silently. This is the only unguarded data-destroying statement in the migration set (everything else
is table/constraint work in a first-migration downgrade, which is expected). Hand-researched
statements are the ones a human produced and cannot be re-derived by re-running the pipeline.
**Fix:** raise instead, with a message naming the rows and telling the operator to delete them
deliberately - a downgrade that refuses is recoverable, a downgrade that deletes is not. Migration
files are the lead's to edit.

### N5. The revalidate route has no rate limit and no minimum secret length

`apps/web/app/api/revalidate/route.ts` is the only non-static route in the web app. The comparison
is `timingSafeEqual` and fails closed when unconfigured, which is right, but nothing throttles
guesses and nothing enforces a length on `REVALIDATE_SECRET` (`packages/core/core/settings.py:64`
accepts any string, unlike `admin_token` which has the 32-byte floor). Impact is bounded - the worst
outcome is forced cache invalidation - but it is an unauthenticated POST on the public origin.
**Fix:** apply the same >= 32-byte floor to `revalidate_secret` in the settings validator, and add
Vercel WAF rate limiting or a small in-memory limiter on the route.

### N6. CORS headers make the API awkward for the browser clients it is aimed at

`apps/api/app/main.py:93-101` sets no `expose_headers`, so `X-Total-Count` (set by `orgs.py:92`,
`responders.py:329`, `statements.py:153`) and `ETag` are invisible to browser JavaScript - and
`If-None-Match` is not in `allow_headers`, so a JS client doing an explicit conditional GET fails
preflight. `cors_origins` also defaults to `[]` (`settings.py:53`) with no production check, so a
forgotten variable means no browser origin works at all. None of this affects the Next.js app, which
fetches server-side, but this is a public open-data API and third-party browser clients are the
point. **Fix:** `expose_headers=["ETag", "X-Total-Count"]`, add `If-None-Match` to `allow_headers`,
and log a warning at start-up when `env == "production"` and `cors_origins` is empty.

### N7. The ETag/304 path is correct; one small note

Verified working end to end - `GET /v1/orgs?limit=1` returned an ETag, the conditional repeat
returned `304` with a zero-length body and the ETag preserved. The `no-store` guard
(`middleware.py:28`) correctly keeps admin responses out of it, and buffering the body is fine at
this payload size. Note only: the 304 is built from `dict(response.headers)`
(`middleware.py:37-40`), which collapses repeated header names to one. Nothing in this API emits
repeated headers today, so this is latent, not live - but `Vary` is the header that will eventually
appear more than once. **Fix:** copy with `response.headers.raw` or a `MutableHeaders`, or leave it
and add a comment recording the assumption.

### N8. `pipeline/probes/common.py` reads a neighbouring project's secrets

The requirement as written is met: `packages/core/core/settings.py` contains no `.env.platform` and
no `AthenaRun` path, and `packages/core/tests/test_settings.py` parses the module to enforce that.
`ADMIN_TOKEN`, `DATABASE_URL` and the LLM key come only from the environment or `./.env.spenden`.
**PASS on the stated rule.** But `pipeline/probes/common.py:119-130` (`platform_key`) does fall back
to `../AthenaRun/.env.platform`, for `IATI_EXPLORATORY_KEY`, `UK_CHARITY_COMMISSION_API_KEY`,
`FIRECRAWL_API_KEY` and `SCRAPER_API_KEY`. It is documented (`machbarkeit-report.md:135,193`),
research-phase only, excluded from ruff (`ruff.toml:7`), and reaches no product credential - so this
is a recorded observation, not a violation. Worth knowing that a checkout of this repo on a machine
without the sibling directory behaves differently, and that `spotcheck()` sends researched URLs to
Firecrawl/ScraperAPI on a key belonging to a different project. **Fix (optional):** drop the second
path from the tuple and require the keys in `.env.spenden`, so the repo is self-contained.

### N9. `.env.example` documents only the research keys

It lists the four probe keys and omits `ADMIN_TOKEN`, `DATABASE_URL`, `OPENROUTER_API_KEY`,
`REVALIDATE_SECRET`, `CORS_ORIGINS` and `ENV` - the ones a Railway deploy actually needs, and the
ones whose absence fails a production start. **Fix:** add them with empty values and a one-line
comment each; it is the checklist the PO-5 deploy will otherwise be assembled from memory.

### N10. Repeatable query parameters are uncapped

`org_type` and `verification` (`responders.py:71-72`, `orgs.py:36`) are `list[str]` with no cap on
count or item length; `district` validates each item but does not cap the list. Probed: 3000
`org_type` values and a single 40000-character value both returned 200, not 500 - the practical
ceiling is the server's request-line limit, well under Postgres's 65535 bind-parameter limit.
Low severity on its own, but it multiplies with B1 while B1 is open. **Fix:** `Query(max_length=50)`
on the lists and `StringConstraints(max_length=40)` on the items.

### N11. The test suite dirties a tracked data file

`pytest` rewrites `data/raw/orgs/_validation.json` with a new `retrieved_at` (via
`pipeline/tests/test_probes_still_work.py`), so a clean checkout has a modified tracked file after
every run. Restored during this review; it is how an unrelated file ends up in someone's commit.
**Fix:** point the probe at `tmp_path` in the test, or have `dump_json` take an output directory.

---

## What was checked and found clean

Recorded so the next reviewer does not repeat it: authorization on all 15 routes (14 GET public by
design, 1 POST token-guarded, no other write route exists); error bodies (422s echo only the
caller's own input, no internals; `/health/ready` returns `unreachable` and logs only the exception
type, never the DSN - `health.py:34-41`); input validation (`limit` capped at 100 with a 422,
`offset >= 0`, `sort` and `hq` as `Literal` enums, district codes pattern-matched per item, `q`
capped at 80 characters); the ETag/304 path (working, verified); the migration set (no destructive
`upgrade` path; the one destructive `downgrade` is N4); `settings.py` (no cross-project fallback);
and the full local suite - `ruff check`, `ruff format --check`, `485 passed`, `pip-audit` clean,
OpenAPI contract current, gitleaks clean.
