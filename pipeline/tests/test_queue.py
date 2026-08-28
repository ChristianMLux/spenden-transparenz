"""Draining the ingestion_run queue.

The admin endpoint writes a row with status "queued" and runs nothing. That is the right design -
the API never imports the pipeline, and no HTTP connection is held open by a slow job - but it is
only honest if something drains the queue. Nothing did until this module existed: `accepted: true`
was a promise the system had no way of keeping, which is worse than a 503 because it looks like
success.
"""

from __future__ import annotations

import uuid

import pytest
from core.models import IngestionRun
from sqlalchemy import func, select

from pipeline.queue import claim_next_queued_run, drain_queue
from pipeline.runs import run_context

pytestmark = pytest.mark.anyio


def _factory_cm(factory):
    """cli.tick opens the session factory as an async context manager; the test already has one."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _cm(database_url=None):
        yield factory

    return _cm


async def _queue(session, job: str) -> uuid.UUID:
    run = IngestionRun(job=job, status="queued")
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run.id


def _job_writing(rows: int):
    async def job(session_factory, handle=None):
        if handle is None:
            async with run_context(session_factory, "test") as opened:
                handle = opened
        handle.count(written=rows)

    return job


async def test_a_queued_run_is_executed_and_closed(job_sessionmaker, session):
    """The whole point: what the admin endpoint accepted actually happens."""
    run_id = await _queue(session, "seed_reference")
    calls: list[uuid.UUID] = []

    async def job(session_factory, handle=None):
        calls.append(handle.id)
        handle.count(written=7)

    executed = await drain_queue(job_sessionmaker, {"seed_reference": job})

    assert executed == 1
    assert calls == [run_id]
    row = await session.get(IngestionRun, run_id)
    await session.refresh(row)
    assert row.status == "succeeded"
    assert row.rows_written == 7
    assert row.finished_at is not None


async def test_the_job_reports_into_the_queued_row_not_a_second_one(job_sessionmaker, session):
    """Two rows for one request would make /v1/meta/freshness count a run that never ran, and
    leave the queued row pending forever."""
    run_id = await _queue(session, "seed_reference")

    await drain_queue(job_sessionmaker, {"seed_reference": _job_writing(3)})

    total = await session.scalar(select(func.count()).select_from(IngestionRun))
    assert total == 1
    row = await session.get(IngestionRun, run_id)
    await session.refresh(row)
    assert row.status == "succeeded"


async def test_the_oldest_queued_run_goes_first(job_sessionmaker, session):
    order: list[str] = []

    async def job(session_factory, handle=None):
        row = await session.get(IngestionRun, handle.id)
        await session.refresh(row)
        order.append(row.job)

    first = await _queue(session, "seed_reference")
    second = await _queue(session, "ingest_orgs")
    assert first != second

    await drain_queue(job_sessionmaker, {"seed_reference": job, "ingest_orgs": job})

    assert order == ["seed_reference", "ingest_orgs"]


async def test_a_claimed_run_is_marked_running_before_the_job_starts(job_sessionmaker, session):
    """A second cron tick that arrives mid-job must not take the same row."""
    await _queue(session, "seed_reference")
    seen: list[str] = []

    async def job(session_factory, handle=None):
        row = await session.get(IngestionRun, handle.id)
        await session.refresh(row)
        seen.append(row.status)

    await drain_queue(job_sessionmaker, {"seed_reference": job})
    assert seen == ["running"]


async def test_a_failing_job_closes_its_own_row_and_the_tick_continues(job_sessionmaker, session):
    """One bad request must not strand the ones queued behind it."""
    failing_id = await _queue(session, "seed_reference")
    good_id = await _queue(session, "ingest_orgs")

    async def boom(session_factory, handle=None):
        raise RuntimeError("boom")

    executed = await drain_queue(job_sessionmaker, {"seed_reference": boom, "ingest_orgs": _job_writing(2)})

    assert executed == 2
    failed = await session.get(IngestionRun, failing_id)
    await session.refresh(failed)
    assert failed.status == "failed"
    assert "boom" in failed.error

    good = await session.get(IngestionRun, good_id)
    await session.refresh(good)
    assert good.status == "succeeded"
    assert good.rows_written == 2


async def test_a_run_for_an_unregistered_job_is_closed_as_failed_not_left_queued(job_sessionmaker, session):
    """A row nothing will ever execute must stop looking like pending work."""
    run_id = await _queue(session, "a_job_that_was_renamed")

    executed = await drain_queue(job_sessionmaker, {})

    assert executed == 1
    row = await session.get(IngestionRun, run_id)
    await session.refresh(row)
    assert row.status == "failed"
    assert "unregistered job" in row.error


async def test_an_empty_queue_is_a_no_op(job_sessionmaker, session):
    assert await drain_queue(job_sessionmaker, {}) == 0
    assert await session.scalar(select(func.count()).select_from(IngestionRun)) == 0


async def test_a_tick_drains_at_most_max_runs(job_sessionmaker, session):
    """A long queue, or a job failing fast in a loop, must not make one tick run forever. What is
    left stays queued for the next tick, still oldest first."""
    for _ in range(4):
        await _queue(session, "seed_reference")

    executed = await drain_queue(job_sessionmaker, {"seed_reference": _job_writing(1)}, max_runs=2)

    assert executed == 2
    still_queued = await session.scalar(
        select(func.count()).select_from(IngestionRun).where(IngestionRun.status == "queued")
    )
    assert still_queued == 2


async def test_a_running_or_finished_run_is_never_claimed(job_sessionmaker, session):
    """Only "queued" is a request to execute. Claiming a running row would double-run a job, and
    claiming a finished one would rewrite history."""
    session.add_all(
        [
            IngestionRun(job="seed_reference", status="running"),
            IngestionRun(job="seed_reference", status="succeeded"),
            IngestionRun(job="seed_reference", status="failed"),
        ]
    )
    await session.commit()

    assert await claim_next_queued_run(job_sessionmaker) is None


# --- the cron tick -------------------------------------------------------------------------------


def test_the_tick_sequence_is_in_dependency_order():
    """A report has to exist before its body can be fetched, a body before it can be extracted, a
    statement before it can be matched or resolved. seed_reference and ingest_orgs are absent on
    purpose: they load files from the repository, so running them every 30 minutes is work
    guaranteed to write nothing."""
    from pipeline.cli import JOBS, TICK_SEQUENCE

    assert TICK_SEQUENCE == (
        "ingest_reliefweb_listing",
        "fetch_report_bodies",
        "extract_statements",
        "match_orgs",
        "resolve_districts",
    )
    assert set(TICK_SEQUENCE) <= set(JOBS)
    assert "seed_reference" not in TICK_SEQUENCE
    assert "ingest_orgs" not in TICK_SEQUENCE


async def test_the_tick_drains_before_it_runs_the_schedule(job_sessionmaker, session, monkeypatch):
    """Someone pressing the admin trigger is asking for something now. Making them wait behind a
    full scheduled sequence would defeat the point of the endpoint."""
    import pipeline.cli as cli_module

    order: list[str] = []

    async def queued_job(session_factory, handle=None):
        order.append("drained")

    async def scheduled(name):
        async def job(session_factory, handle=None):
            order.append(name)
            if handle is None:
                async with run_context(session_factory, name):
                    pass

        return job

    await _queue(session, "seed_reference")
    jobs = {"seed_reference": queued_job}
    for name in cli_module.TICK_SEQUENCE:
        jobs[name] = await scheduled(name)
    monkeypatch.setattr(cli_module, "JOBS", jobs)

    async with job_sessionmaker() as _:
        pass
    monkeypatch.setattr(cli_module, "session_factory", _factory_cm(job_sessionmaker))

    await cli_module.tick()

    assert order[0] == "drained"
    assert order[1:] == list(cli_module.TICK_SEQUENCE)


async def test_one_failing_job_does_not_abort_the_tick(job_sessionmaker, session, monkeypatch):
    """The sequence is ordered by dependency, not by transaction. If the listing fetch fails,
    extracting the bodies already in the database is still the right thing to do."""
    import pipeline.cli as cli_module

    ran: list[str] = []

    def make(name, fail=False):
        async def job(session_factory, handle=None):
            if fail:
                raise RuntimeError(f"{name} exploded")
            ran.append(name)
            async with run_context(session_factory, name):
                pass

        return job

    jobs = {name: make(name, fail=(name == "fetch_report_bodies")) for name in cli_module.TICK_SEQUENCE}
    monkeypatch.setattr(cli_module, "JOBS", jobs)
    monkeypatch.setattr(cli_module, "session_factory", _factory_cm(job_sessionmaker))

    await cli_module.tick()

    assert "fetch_report_bodies" not in ran
    assert ran == [n for n in cli_module.TICK_SEQUENCE if n != "fetch_report_bodies"]
