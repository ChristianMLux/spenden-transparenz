# Build context is the REPOSITORY ROOT. See apps/api/Dockerfile for why - the same reason applies
# here, with one addition: the jobs read data files from the repository at runtime, not only at
# build time. seed_reference reads data/raw/hapi/admin2_NPL.json and data/sources-catalog.json,
# and ingest_orgs reads data/orgs/*.json. pipeline/migrations/add_gap_reason.py resolves those
# through REPO = parents[1], so the layout below has to keep data/ as a sibling of pipeline/.
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pipeline/requirements.txt ./pipeline/requirements.txt
RUN pip install --require-hashes -r pipeline/requirements.txt

COPY packages/core ./packages/core
RUN pip install --no-deps ./packages/core

COPY pipeline ./pipeline
COPY data ./data
COPY schema ./schema

# A cron service, not a server: Railway runs this command and the container exits when it
# finishes. runs.py calls `git rev-parse HEAD` for the git_sha column; there is no .git here, and
# it already returns None rather than failing when git is absent.
CMD ["python", "-m", "pipeline.cli", "tick"]
