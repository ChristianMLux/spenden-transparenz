"""Run every check CI would run, in order, and stop at the first failure.

    python scripts/verify.py           # everything except gitleaks (needs Docker)
    python scripts/verify.py --full    # everything, gitleaks included

GitHub Actions cannot run on this repository while the account is billing-locked, so the gate
evidence has to be produced locally. One command that runs the same steps in the same order is the
difference between evidence anyone can reproduce and a list of commands each person assembles from
memory - and a step quietly left out of that list is exactly how a red check becomes a green claim.

Prints a summary table and exits non-zero if anything failed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

Step = tuple[str, list[str]]

STEPS: list[Step] = [
    ("ruff check", ["uv", "run", "ruff", "check", "."]),
    ("ruff format", ["uv", "run", "ruff", "format", "--check", "."]),
    ("pytest", ["uv", "run", "pytest", "-q"]),
    (
        "pip-audit",
        # --python 3.13 is required: pip-audit builds an ephemeral venv, and on another minor
        # version pip picks wheels whose hashes are not in a lock resolved for 3.13, which fails
        # as a hash mismatch that reads like tampering.
        [
            "uvx",
            "--python",
            "3.13",
            "pip-audit",
            "--requirement",
            "apps/api/requirements.txt",
            "--requirement",
            "pipeline/requirements.txt",
        ],
    ),
    ("openapi contract is current", ["uv", "run", "python", "apps/api/scripts/export_openapi.py"]),
]

GITLEAKS: Step = (
    "gitleaks",
    [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{REPO}:/repo",
        "zricethezav/gitleaks:latest",
        "detect",
        "-s",
        "/repo",
        "--no-git",
        "--no-banner",
        "--redact",
        "-c",
        "/repo/.gitleaks.toml",
    ],
)


def run(name: str, command: list[str]) -> tuple[bool, float]:
    print(f"\n=== {name} ===", flush=True)
    started = time.monotonic()
    # MSYS_NO_PATHCONV stops Git Bash on Windows rewriting /repo into a Windows path.
    env = {"MSYS_NO_PATHCONV": "1"}
    completed = subprocess.run(command, cwd=REPO, env={**_environ(), **env}, check=False)  # noqa: S603
    return completed.returncode == 0, time.monotonic() - started


def _environ() -> dict[str, str]:
    import os

    return dict(os.environ)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the checks CI would run.")
    parser.add_argument("--full", action="store_true", help="include gitleaks (requires Docker)")
    args = parser.parse_args()

    steps = list(STEPS)
    if args.full:
        if shutil.which("docker"):
            steps.append(GITLEAKS)
        else:
            print("docker not found: skipping gitleaks", file=sys.stderr)

    results: list[tuple[str, bool, float]] = []
    for name, command in steps:
        ok, seconds = run(name, command)
        results.append((name, ok, seconds))
        if not ok:
            break

    print("\n=== summary ===")
    for name, ok, seconds in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:32} {seconds:6.1f}s")
    skipped = len(steps) - len(results)
    if skipped:
        print(f"  ....  {skipped} step(s) not run - stopped at the first failure")

    failed = [name for name, ok, _ in results if not ok]
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
