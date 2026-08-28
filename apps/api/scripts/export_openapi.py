"""Write apps/api/openapi.json from the app.

    python apps/api/scripts/export_openapi.py

The committed file is the web team's contract; a test fails when it drifts from the app. Keys are
sorted and the file is written with LF so the diff shows what changed rather than how it was
serialised.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from app.main import create_app  # noqa: E402 - after the path is set up

OUT = API_DIR / "openapi.json"


def main() -> int:
    spec = create_app().openapi()
    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(spec, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"wrote {OUT} with {len(spec['paths'])} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
