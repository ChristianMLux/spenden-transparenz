"""The research probes moved from scripts/ to pipeline/probes/ and are frozen there.

The move redefines what `common.ROOT` resolves to, so these tests guard the one thing that
could silently break: every probe writes into data/raw/<source>/ relative to ROOT.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_common_root_points_at_the_repo_root():
    out = subprocess.run(
        [sys.executable, "-c", "from common import ROOT; print(ROOT)"],
        cwd=REPO / "pipeline" / "probes",
        capture_output=True,
        text=True,
        check=True,
    )
    assert Path(out.stdout.strip()) == REPO


def test_validate_orgs_shim_runs_and_reports_zero_schema_errors():
    subprocess.run(
        [sys.executable, "scripts/validate_orgs.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads((REPO / "data" / "raw" / "orgs" / "_validation.json").read_text(encoding="utf-8"))["data"]
    assert report["schema_errors"] == 0
    assert report["orgs"] == 44
