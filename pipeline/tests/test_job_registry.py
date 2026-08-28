"""core.jobs.JOB_NAMES and pipeline.cli.JOBS must agree, in both directions.

A name in JOB_NAMES with no entry in JOBS is a queued run nothing will ever drain: the admin
endpoint (apps/api) accepts the name, writes an ingestion_run with status "queued", and the
pipeline's next tick has nothing registered to run it - it sits forever. A name in JOBS with no
entry in JOB_NAMES is reachable from the CLI but not from the admin endpoint, which is a smaller
problem but still a drift between the two services' idea of what jobs exist.

core/jobs.py's own docstring already claimed this test existed ("so the pipeline has a test that
the two agree") before it did - three jobs (extract_statements, match_orgs, resolve_districts)
were implemented, tested, and merged, but their pipeline/cli.py registration fell through a file-
ownership gap (cli.py belongs to WP-A) and was never added. Caught by the backend lead during
review: a queued run with no implementation to drain it does not raise or log anything on its
own, so this is exactly the kind of drift a docstring's claim, unverified, does not actually
prevent.
"""

from __future__ import annotations

from core.jobs import JOB_NAMES

from pipeline.cli import JOBS


def test_every_job_name_has_a_registered_implementation():
    missing = set(JOB_NAMES) - set(JOBS)
    assert missing == set(), f"queued runs for these jobs would never drain: {sorted(missing)}"


def test_every_registered_job_is_a_known_job_name():
    unknown = set(JOBS) - set(JOB_NAMES)
    assert unknown == set(), f"reachable from the CLI but not from the admin endpoint: {sorted(unknown)}"


def test_job_names_and_jobs_agree_exactly():
    assert set(JOB_NAMES) == set(JOBS)
