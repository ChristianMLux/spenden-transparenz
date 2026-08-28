"""Shared helpers for the data-source probes.

Every probe: one HTTP call per endpoint, raw response to disk with a
`retrieved_at` stamp, all analysis offline from the saved file.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
TODAY = date.today().isoformat()
FLOOD_DATE = date(2026, 8, 26)

UA = "spenden-transparenz-research/0.1 (chris.lux.st@gmail.com)"


def session(timeout: int = 60) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"})
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.request = _with_timeout(s.request, timeout)  # type: ignore[method-assign]
    return s


def _with_timeout(fn, timeout):
    def inner(method, url, **kw):
        kw.setdefault("timeout", timeout)
        return fn(method, url, **kw)
    return inner


def out_dir(source: str) -> Path:
    d = RAW / source
    d.mkdir(parents=True, exist_ok=True)
    return d


def dump_json(source: str, name: str, payload, meta: dict | None = None) -> Path:
    """Write payload wrapped with provenance metadata."""
    path = out_dir(source) / f"{name}.json"
    wrapper = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        **(meta or {}),
        "data": payload,
    }
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=1)
    return path


def dump_bytes(source: str, name: str, content: bytes) -> Path:
    path = out_dir(source) / name
    path.write_bytes(content)
    return path


def load_json(source: str, name: str):
    path = RAW / source / f"{name}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)["data"]


def fill_rate(rows: list[dict], fields: list[str]) -> dict[str, float]:
    """Share of rows where field is non-empty. One pass, no per-field rescans."""
    n = len(rows)
    if n == 0:
        return {f: 0.0 for f in fields}
    counts = dict.fromkeys(fields, 0)
    for r in rows:
        for f in fields:
            v = r.get(f)
            if v not in (None, "", [], {}):
                counts[f] += 1
    return {f: round(counts[f] / n, 3) for f in fields}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def summary(source: str, payload: dict) -> Path:
    """Machine-readable summary the report is written from."""
    return dump_json(source, "_summary", payload)


def days_since_flood(d: str | None) -> int | None:
    if not d:
        return None
    try:
        return (date.fromisoformat(d[:10]) - FLOOD_DATE).days
    except ValueError:
        return None


def paced(iterable, seconds: float = 0.3):
    for x in iterable:
        yield x
        time.sleep(seconds)


def platform_key(name: str) -> str:
    """Secret from the environment, else ./.env.spenden, else ../AthenaRun/.env.platform (all local, gitignored). Empty string if absent."""
    import os
    if os.environ.get(name):
        return os.environ[name]
    for env_file in (ROOT / ".env.spenden", ROOT.parent / "AthenaRun" / ".env.platform"):
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                k, _, v = line.partition("=")
                if k.strip() == name and v.strip():
                    return v.strip().strip('"').strip("'")
    return ""
