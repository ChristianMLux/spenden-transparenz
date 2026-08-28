"""The job names both services agree on.

The API must not import the pipeline package. They are separate Railway services with separate
deploy artefacts, and the pipeline carries the LLM credentials and the network fetchers - none of
which belong in a read-only public API's image. So the one thing they genuinely share, the set of
job names, lives here in core instead.

The admin endpoint validates a name against this tuple and records an `ingestion_run` with status
"queued". It runs nothing in process. The pipeline service drains queued runs at the start of its
next tick, oldest first, marking each "running" as it takes it. That keeps the API read-only in
practice, keeps a minutes-long extraction out of a web request, and makes a double-click on the
admin button harmless.

Adding a job means adding its name here and registering the callable in pipeline/cli.py. A name
here with no implementation is a queued run nothing will ever drain, so the pipeline has a test
that the two agree.
"""

from __future__ import annotations

JOB_NAMES: tuple[str, ...] = (
    "seed_reference",
    "ingest_orgs",
    "ingest_reliefweb_listing",
    "fetch_report_bodies",
    "extract_statements",
    "match_orgs",
    "resolve_districts",
)
