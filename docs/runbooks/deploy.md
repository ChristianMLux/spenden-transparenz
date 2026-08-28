# Deploying to Railway (PO-5)

Project `spenden-transparenz`, id `2d9bcd11-b35c-41fe-81c3-e2d5aafc509f`, environment `production`
`46ff140e-e5b7-4651-b052-30f12cbb55d1`, personal workspace. The `Postgres` service already exists
(private host `postgres.railway.internal`).

Two services are added: **api** (HTTP) and **pipeline** (cron). Everything below is committed to
the repository; what remains is creating the services and setting variables.

## The one non-obvious decision: Root Directory stays at the repository root

Both services import `core` from `packages/core`, a uv workspace member outside either service
directory. The service `requirements.txt` files are exported with `--no-emit-workspace`, so they
pin every third-party dependency and deliberately contain no entry for `spenden-core` - it is
installed from source in the Dockerfile.

That rules out the obvious layout. Railway's monorepo documentation says of Root Directory:
*"Setting this means that Railway will only pull down files from that directory when creating new
deployments."* A Root Directory of `apps/api` would cut `packages/core` out of the build context
entirely, and no build step inside that context can reach `../../packages/core`.

The same page resolves it: *"The Railway Config File does not follow the Root Directory path. You
have to specify the absolute path for the `railway.json` or `railway.toml` file."* So the config
path is set per service, independently of Root Directory:

| service | Root Directory | Railway Config File | Dockerfile |
|---|---|---|---|
| api | `/` (repository root) | `/apps/api/railway.toml` | `apps/api/Dockerfile` |
| pipeline | `/` (repository root) | `/pipeline/railway.toml` | `pipeline/Dockerfile` |

`watchPatterns` in each `railway.toml` keeps a pipeline change from rebuilding the API and vice
versa, which is what Root Directory would otherwise have given us.

Docker rather than Nixpacks, for both: the build is explicit, and both images were built and run
locally against the real database before this was written. Nixpacks at the repository root would
have to infer the right thing from a uv workspace, and an inference that only fails on Railway is
the worst possible place to find out.

## Creating the services

```
railway link                     # select spenden-transparenz / production
railway add --service api      --repo ChristianMLux/spenden-transparenz --branch main
railway add --service pipeline --repo ChristianMLux/spenden-transparenz --branch main

railway environment edit --service-config api      source.rootDirectory /
railway environment edit --service-config pipeline source.rootDirectory /
```

Then set each service's **Config as Code** path (`/apps/api/railway.toml`, `/pipeline/railway.toml`)
in the service settings. Everything else - builder, start command, cron schedule, healthcheck,
pre-deploy migration, restart policy - comes from those files and needs no dashboard entry.

**Region:** the `Postgres` service was created in Railway's default region. Create api and pipeline
in the **same region**. They reach Postgres over the private network (`postgres.railway.internal`),
which does not cross regions - a cross-region service fails to connect rather than merely being
slow.

## Variables

Use Railway reference variables rather than copied values: the password then rotates with the
database instead of silently going stale. The Postgres service exposes `PGUSER`, `PGPASSWORD` and
`PGDATABASE`; reference them as `${{Postgres.PGUSER}}` and so on.

### api

| name | value |
|---|---|
| `ENV` | `production` |
| `DATABASE_URL` | `postgresql+asyncpg://<PGUSER-ref>:<PGPASSWORD-ref>@postgres.railway.internal:5432/<PGDATABASE-ref>` |
| `DATABASE_URL_SYNC` | `postgresql+psycopg://<PGUSER-ref>:<PGPASSWORD-ref>@postgres.railway.internal:5432/<PGDATABASE-ref>` |
| `ADMIN_TOKEN` | from `.env.spenden` |
| `CORS_ORIGINS` | a **JSON list string**, e.g. `["https://spenden-transparenz.vercel.app"]` |
| `LOG_LEVEL` | `INFO` |

`DATABASE_URL_SYNC` is not optional here: the pre-deploy `alembic upgrade head` runs through
psycopg while the app itself uses asyncpg. Without it the release fails before it starts.

`CORS_ORIGINS` must be a JSON list string. A bare `https://example.org` is a validation error at
start-up, not a one-element list - the PO hit exactly this during PO-3.

### pipeline

| name | value |
|---|---|
| `ENV` | `production` |
| `DATABASE_URL` | the same asyncpg reference URL as the api |
| `DATABASE_URL_SYNC` | the same psycopg reference URL as the api |
| `OPENROUTER_API_KEY` | from `.env.spenden` |
| `LLM_MODEL` | `anthropic/claude-sonnet-5` |
| `MAX_REPORTS_PER_RUN` | `25` |
| `MAX_RUN_COST_USD` | `1.00` |
| `WEB_BASE_URL` | the Vercel production URL, no trailing slash |
| `REVALIDATE_SECRET` | from `.env.spenden`, identical to the value the web app holds |
| `LOG_LEVEL` | `INFO` |

`MAX_RUN_COST_USD` is a cap **per run**, not per tick or per day. A tick runs `extract_statements`
once, so the ceiling is one dollar per tick - at `*/30` that is a theoretical 48 dollars a day. In
practice a tick with nothing new to extract spends nothing, because the job's candidate query
returns no reports. Watch `sum(cost_usd)` on `ingestion_run` for the first day rather than
assuming it.

`WEB_BASE_URL` and `REVALIDATE_SECRET` are what the revalidate hook needs. Unset, the pipeline logs
`revalidate_skipped_not_configured` and carries on - the data stays correct, the web app's cache
just goes stale.

## What the cron actually runs

`python -m pipeline.cli tick`, every 30 minutes:

1. **Drain** whatever the admin endpoint queued, oldest first, at most 5 per tick. Queued work goes
   first, because someone pressing the trigger is asking for something now.
2. **The scheduled sequence**, in dependency order:
   `ingest_reliefweb_listing` then `fetch_report_bodies` then `extract_statements` then
   `match_orgs` then `resolve_districts`.

Each job opens its own `ingestion_run`, so `/v1/meta/freshness` reports per job rather than per
tick. One failing job does not abort the tick: the sequence is ordered by dependency, not by
transaction, and each failure is already recorded on its own run row.

`seed_reference` and `ingest_orgs` are deliberately **not** in the tick. They load files from the
repository, so they change only when a deploy changes them; running them every 30 minutes would be
work guaranteed to write nothing. Run them once after the first deploy, and after any deploy that
changes `data/`:

```
railway run --service pipeline python -m pipeline.cli run seed_reference
railway run --service pipeline python -m pipeline.cli run ingest_orgs
```

Measured locally, in the built image against the real database: a tick with nothing new took
**16 seconds** and all five jobs wrote 0 rows.

## The migration-ordering hazard

The API returns **HTTP 500 on every board request** when the database schema is behind the code,
and `/health` stays green throughout because it deliberately never touches Postgres. This is not
hypothetical - it happened locally with code at 0006 and a database at 0005:

```
asyncpg.exceptions.UndefinedColumnError: column org_datum.channel_type does not exist
```

Three defences, in order:

1. `preDeployCommand = ["alembic", "upgrade", "head"]` in `apps/api/railway.toml`. A failing
   pre-deploy blocks the release, which is the point.
2. The app logs `schema_behind_code` at start-up with both revisions when they differ, and
   `schema_revision_ok` when they match. Grep the deploy logs for it.
3. `/health/ready` reports `alembic_revision`. Compare it with the code's head after any deploy
   that adds a migration.

It warns rather than refusing to start, deliberately: a hard exit would turn a migration that has
not run yet into a full outage, and a deployment that can still serve `/health/ready` and its
unaffected routes is more useful than one that will not boot.

## PO-5 verification

```
curl -s https://<api-domain>/health
curl -s https://<api-domain>/health/ready
curl -s https://<api-domain>/v1/meta/freshness
curl -s "https://<api-domain>/v1/disasters/ff-2026-000162-npl/responders?limit=5"
curl -s -o /dev/null -w "%{http_code}" -X POST https://<api-domain>/v1/admin/ingest/seed_reference
```

Expected: status ok; database ok with an `alembic_revision`; every job under 1 h after a tick; a
board page; and `401` for the admin call without a token.

In the database, one tick visible:

```sql
select job, status, rows_written, finished_at
from ingestion_run
where started_at > now() - interval '1 hour'
order by started_at;
```

## Verified locally before this was written

Both images built from the repository root and run against the live Postgres:

```
$ docker build -f apps/api/Dockerfile  -t spenden-api:verify .        # DONE
$ docker build -f pipeline/Dockerfile  -t spenden-pipeline:verify .   # DONE

$ docker run ... spenden-pipeline:verify                 # a full tick
tick_drained     executed 0
ingest_reliefweb_listing  succeeded  written 0  skipped 77
fetch_report_bodies       succeeded  written 0
extract_statements        succeeded  written 0  skipped 2
match_orgs                succeeded  written 0  skipped 210
resolve_districts         succeeded  written 0  skipped 227
tick_finished    drained 0  ran 5  failed []          # 16 seconds

$ docker run ... spenden-api:verify   (ENV=production)
schema_revision_ok     revision 0006
/health                -> {"status":"ok"}
/health/ready          -> {"database":"ok","alembic_revision":"0006"}
/v1/.../responders     -> 200, 98 items, 0 missing donation_channel, 34 non-null
POST /v1/admin/ingest  -> 401 without a token
headers                -> nosniff, no-referrer, no Server banner
```

`ENV=production` in that run also exercised the start-up secret validation: the API refuses to
start without `ADMIN_TOKEN` and `DATABASE_URL`.
