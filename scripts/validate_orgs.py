"""Moved to pipeline/probes/validate_orgs.py. This shim keeps the documented entry point working.

Usage is unchanged:
    python scripts/validate_orgs.py
    python scripts/validate_orgs.py --spotcheck 0.12
"""

import runpy
import sys
from pathlib import Path

PROBES = Path(__file__).resolve().parents[1] / "pipeline" / "probes"
sys.path.insert(0, str(PROBES))
runpy.run_path(str(PROBES / "validate_orgs.py"), run_name="__main__")
