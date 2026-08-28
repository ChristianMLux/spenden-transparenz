# Build context is the REPOSITORY ROOT, not apps/api.
#
# Both services import `core` from packages/core, a uv workspace member. The service
# requirements.txt files are exported with --no-emit-workspace, so they pin every third-party
# dependency and deliberately contain no entry for spenden-core itself - it is installed from
# source below. Railway's Root Directory cannot be apps/api for that reason: setting it means
# "Railway will only pull down files from that directory", which would cut packages/core out of
# the build entirely. Root Directory stays at the repository root and this file is selected per
# service through the Railway config path, which the docs state does not follow Root Directory.
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Two pip invocations, not one. The requirements file carries --hash pins, and pip refuses to mix
# hashed requirements with an unhashed local path in the same command.
COPY apps/api/requirements.txt ./apps/api/requirements.txt
RUN pip install --require-hashes -r apps/api/requirements.txt

COPY packages/core ./packages/core
RUN pip install --no-deps ./packages/core

COPY apps/api ./apps/api

# Alembic resolves script_location relative to alembic.ini, and the app is started from the same
# directory, so both the pre-deploy migration and the server run from here.
WORKDIR /app/apps/api

# Documentation only - Railway routes to $PORT, which start.sh reads.
EXPOSE 8000

CMD ["./start.sh"]
