"""The documented setup command must produce an environment that can run everything.

Found at gate PO-0: a fresh clone running the documented `uv sync` got only the root dev group.
Every service test failed on import, and the frozen research probes could not run because
`requests` was not installed. The environment contract was broken for anyone but the person who
happened to have typed `--all-packages`.

The root project therefore depends on spenden-api, which pulls the API and core dependency trees.
`pipeline` is a virtual project (its directory is itself the package, flat layout), so its two
otherwise-unreachable dependencies are repeated in the root dev group. These tests exist so that
duplication cannot drift unnoticed.
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

# Distribution name -> import name, where they differ.
IMPORT_NAME = {
    "python-json-logger": "pythonjsonlogger",
    "pydantic-settings": "pydantic_settings",
    "spenden-core": "core",
    "psycopg[binary]": "psycopg",
    "sqlalchemy[asyncio]": "sqlalchemy",
    "uvicorn[standard]": "uvicorn",
}


def _requirement_names(path: Path) -> list[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    names = []
    for raw in data["project"]["dependencies"]:
        # "sqlalchemy[asyncio]>=2.0.36" -> "sqlalchemy[asyncio]"
        name = raw.split(">=")[0].split("==")[0].split("<")[0].split("~=")[0].strip()
        names.append(name)
    return names


def _import_name(distribution: str) -> str:
    if distribution in IMPORT_NAME:
        return IMPORT_NAME[distribution]
    return distribution.split("[")[0].replace("-", "_")


@pytest.mark.parametrize("distribution", _requirement_names(REPO / "pipeline" / "pyproject.toml"))
def test_every_pipeline_dependency_is_importable(distribution: str):
    """If this fails, a dependency was added to pipeline/pyproject.toml and the root dev group was
    not updated. A plain `uv sync` would then give a fresh clone a broken environment."""
    module = _import_name(distribution)
    assert importlib.util.find_spec(module) is not None, (
        f"{distribution} is declared by pipeline but not installed by a plain `uv sync`. "
        f"Add it to the dev group in the root pyproject.toml."
    )


@pytest.mark.parametrize("distribution", _requirement_names(REPO / "apps" / "api" / "pyproject.toml"))
def test_every_api_dependency_is_importable(distribution: str):
    module = _import_name(distribution)
    assert importlib.util.find_spec(module) is not None, f"{distribution} is declared by apps/api but not installed"


def test_the_frozen_probes_can_actually_run():
    """The probes are documented as runnable and one gate command invokes them through a shim."""
    for module in ("requests", "jsonschema"):
        assert importlib.util.find_spec(module) is not None, f"the research probes need {module}"


def test_the_root_project_pulls_in_the_api_service():
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert "spenden-api" in data["project"]["dependencies"]
