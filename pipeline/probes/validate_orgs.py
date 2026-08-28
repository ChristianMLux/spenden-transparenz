"""Merge the researched org batches, validate against schema/org.schema.json,
compute per-field fill rates + verification-grade distribution, and run a
provenance spot-check (fetch source_url, look for the value on the page).

usage: python validate_orgs.py            # merge + validate + stats
       python validate_orgs.py --spotcheck 0.12   # additionally fetch ~12 % of datums
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

from common import ROOT, dump_json, log, session

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

BATCH_DIR = ROOT / "data" / "orgs"
SCHEMA = json.loads((ROOT / "schema" / "org.schema.json").read_text(encoding="utf-8"))
OUT = ROOT / "orgs-nepal-2026.json"
DATUM_KEYS = {"value", "source_url", "retrieved_at", "verification"}


def load_batches() -> list[dict]:
    orgs, seen = [], {}
    for p in sorted(BATCH_DIR.glob("batch-*.json")):
        try:
            batch = json.loads(p.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            log(f"!! {p.name}: invalid JSON ({e})")
            continue
        for o in batch:
            oid = o.get("org_id")
            if oid in seen:
                log(f"   duplicate org_id {oid}: {p.name} vs {seen[oid]} -> keeping first")
                continue
            seen[oid] = p.name
            o["_batch"] = p.name
            orgs.append(o)
    return orgs


def validate(orgs: list[dict]) -> list[tuple[str, str]]:
    if jsonschema is None:
        log("jsonschema not installed -> structural check only")
        return [(o.get("org_id"), "missing " + k) for o in orgs for k in SCHEMA["required"] if k not in o]
    v = jsonschema.Draft202012Validator(SCHEMA)
    errs = []
    for o in orgs:
        clean = {k: val for k, val in o.items() if not k.startswith("_")}
        for e in v.iter_errors(clean):
            errs.append((o.get("org_id"), f"{'/'.join(str(x) for x in e.absolute_path)}: {e.message[:120]}"))
    return errs


def walk_datums(obj, path=""):
    """Yield (path, datum) for every value-node that carries provenance."""
    if isinstance(obj, dict):
        if DATUM_KEYS <= obj.keys():
            yield path, obj
        for k, v in obj.items():
            yield from walk_datums(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_datums(v, f"{path}[{i}]")


def stats(orgs: list[dict]) -> dict:
    n = len(orgs)
    by_type = Counter(o.get("org_type") for o in orgs)
    by_country = Counter(o.get("hq", {}).get("country") for o in orgs)
    fields = {
        "names.legal": lambda o: (o["names"].get("legal") or {}).get("value"),
        "registrations[any identifier]": lambda o: any(r.get("identifier") for r in o["registrations"]),
        "registrations[NP_SWC identifier]": lambda o: any(r.get("identifier") for r in o["registrations"] if r.get("registry") == "NP_SWC"),
        "nepal_presence.since_year": lambda o: o["nepal_presence"]["since_year"].get("value"),
        "nepal_presence.mode(known)": lambda o: o["nepal_presence"]["mode"].get("value") not in (None, "unknown"),
        "current_response[>=1]": lambda o: len(o["current_response"]) > 0,
        "financial.annual_report.available": lambda o: o["financial_transparency"]["annual_report"].get("available"),
        "financial.audited": lambda o: o["financial_transparency"]["audited_financials"].get("value"),
        "financial.iati_publisher": lambda o: o["financial_transparency"]["iati_publisher"].get("is_publisher"),
        "financial.income": lambda o: o["financial_transparency"]["income"].get("value") is not None,
        "financial.expenditure": lambda o: o["financial_transparency"]["expenditure"].get("value") is not None,
        "financial.program_ratio": lambda o: o["financial_transparency"]["program_ratio"].get("value") is not None,
        "warnings[>=1]": lambda o: len(o["warnings"]) > 0,
    }
    fill = {}
    for name, fn in fields.items():
        ok = 0
        for o in orgs:
            try:
                ok += bool(fn(o))
            except (KeyError, TypeError, AttributeError):
                pass
        fill[name] = round(ok / n, 2) if n else 0
    local = [o for o in orgs if o.get("hq", {}).get("country") == "NP"]
    intl = [o for o in orgs if o.get("hq", {}).get("country") != "NP"]

    def sub(group):
        g = len(group) or 1
        return {k: round(sum(bool(_safe(fn, o)) for o in group) / g, 2) for k, fn in fields.items()}

    verif = Counter(d.get("verification") for o in orgs for _, d in walk_datums(o))
    datums = sum(1 for o in orgs for _ in walk_datums(o))
    with_value = sum(1 for o in orgs for _, d in walk_datums(o) if d.get("value") not in (None, "", []))
    gaps = Counter(re.sub(r"\[\d+\]", "[]", g) for o in orgs for g in o.get("data_gaps", []))
    return {
        "orgs": n, "by_org_type": dict(by_type), "by_hq_country": dict(by_country), "local_np": len(local), "international": len(intl),
        "fill_rate_all": fill, "fill_rate_local_np": sub(local), "fill_rate_international": sub(intl),
        "datums_total": datums, "datums_with_value": with_value, "verification_distribution": dict(verif.most_common()),
        "top_data_gaps": gaps.most_common(12),
        "orgs_with_response": [o["org_id"] for o in orgs if o["current_response"]],
        "orgs_without_any_financial_figure": [o["org_id"] for o in orgs if o["financial_transparency"]["income"].get("value") is None and not o["financial_transparency"]["annual_report"].get("available")],
    }


def _safe(fn, o):
    try:
        return fn(o)
    except (KeyError, TypeError, AttributeError):
        return False


def _scraper_keys() -> dict[str, str]:
    """FIRECRAWL_API_KEY / SCRAPER_API_KEY via common.platform_key (env -> .env.spenden -> AthenaRun/.env.platform)."""
    from common import platform_key
    return {k: v for k in ("FIRECRAWL_API_KEY", "SCRAPER_API_KEY") if (v := platform_key(k))}


def _fetch_via_proxy(S, url: str, keys: dict[str, str]) -> tuple[str, str]:
    """Bot-blocked page -> Firecrawl (markdown) -> ScraperAPI (html). Returns (text, via)."""
    if keys.get("FIRECRAWL_API_KEY"):
        try:
            r = S.post("https://api.firecrawl.dev/v1/scrape", json={"url": url, "formats": ["markdown"]},
                       headers={"Authorization": f"Bearer {keys['FIRECRAWL_API_KEY']}"}, timeout=90)
            if r.status_code == 200:
                md = (r.json().get("data") or {}).get("markdown") or ""
                if md.strip():
                    return md.lower(), "firecrawl"
        except Exception:  # noqa: BLE001
            pass
    if keys.get("SCRAPER_API_KEY"):
        try:
            r = S.get("https://api.scraperapi.com/", params={"api_key": keys["SCRAPER_API_KEY"], "url": url, "render": "true"}, timeout=120)
            if r.status_code == 200 and r.text.strip():
                return re.sub(r"<[^>]+>", " ", r.text).lower(), "scraperapi"
        except Exception:  # noqa: BLE001
            pass
    return "", ""


def spotcheck(orgs: list[dict], share: float, seed: int = 26) -> dict:
    """Fetch a random sample of datum source_urls and look for the value in the page text.
    Direct fetch first; on a non-200 / connection error fall back to Firecrawl, then ScraperAPI."""
    S = session(timeout=40)
    S.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) spenden-transparenz-research/0.1"
    keys = _scraper_keys()
    pool = [(o["org_id"], p, d) for o in orgs for p, d in walk_datums(o) if d.get("source_url") and d.get("value") not in (None, "", [], True, False)]
    random.Random(seed).shuffle(pool)
    sample = pool[: max(1, int(len(pool) * share))]
    results = []
    cache: dict[str, tuple[str, str]] = {}
    for oid, path, d in sample:
        url = d["source_url"]
        if url not in cache:
            try:
                r = S.get(url)
                cache[url] = (re.sub(r"<[^>]+>", " ", r.text).lower(), "direct") if r.status_code == 200 else (f"__HTTP_{r.status_code}__", "")
            except Exception as e:  # noqa: BLE001
                cache[url] = (f"__ERR_{type(e).__name__}__", "")
            if cache[url][0].startswith("__") and keys:
                text, via = _fetch_via_proxy(S, url, keys)
                if text:
                    cache[url] = (text, via)
        page, via = cache[url]
        val = d["value"]
        needle = _needle(val)
        quote = (d.get("quote") or "").lower()[:60]
        status = "http_error" if page.startswith("__") else "value_found" if needle and needle in page else "quote_found" if quote and quote[:40] in page else "not_found"
        results.append({"org": oid, "path": path, "url": url, "value": val if not isinstance(val, str) else val[:80], "result": status, "via": via or page[:20]})
    c = Counter(r["result"] for r in results)
    return {"share": share, "pool": len(pool), "checked": len(results), "counts": dict(c), "via": dict(Counter(r["via"] for r in results)), "results": results}


def _needle(val) -> str:
    if isinstance(val, (int, float)):
        s = str(int(val)) if float(val).is_integer() else str(val)
        return s if len(s) >= 3 else ""
    if isinstance(val, str):
        return val.lower()[:50]
    return ""


def main():
    orgs = load_batches()
    errs = validate(orgs)
    for oid, msg in errs[:60]:
        log(f"   schema: {oid}: {msg}")
    st = stats(orgs)
    result = {"schema_errors": len(errs), "schema_error_samples": errs[:40], **st}
    if "--spotcheck" in sys.argv:
        share = float(sys.argv[sys.argv.index("--spotcheck") + 1])
        result["spotcheck"] = spotcheck(orgs, share)
    else:  # keep the last spot-check so the report's numbers survive a plain re-validation
        prev = ROOT / "data" / "raw" / "orgs" / "_validation.json"
        if prev.exists():
            old = json.loads(prev.read_text(encoding="utf-8")).get("data", {})
            if "spotcheck" in old:
                result["spotcheck"] = old["spotcheck"] | {"note": "carried over from previous run"}
    dump_json("orgs", "_validation", result)
    if not errs:
        clean = [{k: v for k, v in o.items() if not k.startswith("_")} for o in orgs]
        OUT.write_text(json.dumps({"dataset": "Nepal floods 2026 - pilot org records", "schema": "schema/org.schema.json", "generated_at": "2026-08-28", "orgs": clean}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        log(f"wrote {OUT.name} with {len(clean)} orgs")
    log(json.dumps({k: v for k, v in result.items() if k in ("schema_errors", "orgs", "local_np", "international", "verification_distribution", "fill_rate_all")}, ensure_ascii=False, indent=1))
    if "spotcheck" in result:
        log("spotcheck:", result["spotcheck"]["counts"])


if __name__ == "__main__":
    main()
