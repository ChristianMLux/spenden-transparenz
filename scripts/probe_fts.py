"""OCHA FTS (api.hpc.tools, public, no key).

Questions: are 2026 Nepal flood flows visible? pledge/commitment/paid
distinguishable? how big is the reporting lag (decisionDate vs firstReportedDate)?
Baseline: the 2024 Nepal floods plan (id 1265) as a comparison crisis.
"""
from collections import Counter, defaultdict

from common import FLOOD_DATE, days_since_flood, dump_json, log, session, summary

BASE = "https://api.hpc.tools/v1/public"
S = session()
SRC = "fts"
FLOOD_WORDS = ("flood", "trishuli", "rasuwa", "nuwakot", "glacial", "glof", "flash")


def get(path, **params):
    r = S.get(f"{BASE}{path}", params=params)
    r.raise_for_status()
    return r.json()


def all_flows(**params):
    """Follow meta.nextLink until exhausted. One request per page, nothing per flow."""
    flows, page = [], get("/fts/flow", limit=1000, **params)
    while True:
        d = page.get("data", {})
        flows.extend(d.get("flows", []))
        nxt = (page.get("meta") or {}).get("nextLink")
        if not nxt:
            return flows, {k: v for k, v in d.items() if k != "flows"}
        r = S.get(nxt)
        r.raise_for_status()
        page = r.json()


def org_names(objs, role):
    return [o.get("name") for o in objs if o.get("type") == "Organization" and o.get("behavior", role) is not None]


def analyse(flows):
    status = Counter(f.get("status") for f in flows)
    usd_by_status = defaultdict(float)
    for f in flows:
        usd_by_status[f.get("status")] += f.get("amountUSD") or 0
    lags = []
    for f in flows:
        dec, rep = f.get("decisionDate"), f.get("firstReportedDate")
        if dec and rep:
            from datetime import date
            lags.append((date.fromisoformat(rep[:10]) - date.fromisoformat(dec[:10])).days)
    lags.sort()
    med = lags[len(lags) // 2] if lags else None
    dest_types = Counter()
    for f in flows:
        for o in f.get("destinationObjects", []):
            if o.get("type") == "Organization":
                dest_types[(o.get("organizationTypes") or ["?"])[0] if isinstance(o.get("organizationTypes"), list) else str(o.get("organizationTypes"))] += 1
    return {
        "n_flows": len(flows),
        "status_counts": dict(status),
        "usd_by_status": {k: round(v) for k, v in usd_by_status.items()},
        "reporting_lag_days": {"n": len(lags), "median": med, "p90": lags[int(len(lags) * 0.9)] if lags else None, "max": lags[-1] if lags else None},
        "destination_org_types": dict(dest_types.most_common(10)),
    }


def main():
    plans = get("/plan/country/NPL")["data"]
    dump_json(SRC, "plans_npl", plans)
    emergencies = get("/emergency/country/NPL")["data"]
    dump_json(SRC, "emergencies_npl", emergencies)

    flows26, meta26 = all_flows(countryISO3="NPL", year=2026)
    dump_json(SRC, "flows_npl_2026", flows26, {"meta": meta26})
    flood_flows = [
        f for f in flows26
        if (days_since_flood(f.get("date") or f.get("decisionDate")) or -1) >= 0
        or any(w in (f.get("description") or "").lower() for w in FLOOD_WORDS)
        or any(w in (o.get("name") or "").lower() for o in f.get("destinationObjects", []) if o.get("type") == "Emergency" for w in FLOOD_WORDS)
    ]
    dump_json(SRC, "flows_npl_2026_flood_candidates", flood_flows)

    # Baseline: 2024 floods response plan (id 1265) — how did reporting behave in a comparable crisis?
    flows1265, meta1265 = all_flows(planId=1265)
    dump_json(SRC, "flows_plan_1265_floods_2024", flows1265, {"meta": meta1265})

    # Emergency records that FTS created after the 26.08.2026 flood? (none expected yet)
    new_em = [e for e in emergencies if (e.get("date") or "") >= "2026-01-01"]

    fields = ["id", "status", "amountUSD", "date", "decisionDate", "firstReportedDate", "description", "sourceObjects", "destinationObjects", "flowType", "method", "budgetYear"]
    fill = {k: round(sum(1 for f in flows26 if f.get(k) not in (None, "", [])) / max(len(flows26), 1), 3) for k in fields}

    out = {
        "flood_date": FLOOD_DATE.isoformat(),
        "plans_npl": [{"id": p.get("id"), "name": p.get("planVersion", {}).get("name"), "years": [y.get("year") for y in p.get("years", [])]} for p in plans],
        "emergencies_npl_latest": sorted([{"id": e.get("id"), "name": e.get("name"), "date": (e.get("date") or "")[:10], "glide": e.get("glideId")} for e in emergencies], key=lambda x: x["date"], reverse=True)[:3],
        "emergencies_created_2026": new_em,
        "flows_2026": analyse(flows26) | {"meta": meta26},
        "flood_candidate_flows": [{"id": f.get("id"), "status": f.get("status"), "usd": f.get("amountUSD"), "date": (f.get("date") or "")[:10], "reported": (f.get("firstReportedDate") or "")[:10], "desc": (f.get("description") or "")[:120],
                                   "src": [o.get("name") for o in f.get("sourceObjects", []) if o.get("type") == "Organization"][:2],
                                   "dst": [o.get("name") for o in f.get("destinationObjects", []) if o.get("type") == "Organization"][:2]} for f in flood_flows],
        "baseline_floods_2024_plan_1265": analyse(flows1265) | {"meta": meta1265},
        "field_fill_rates_2026": fill,
    }
    summary(SRC, out)
    log("FTS: flows 2026 =", len(flows26), "| flood candidates =", len(flood_flows), "| 2024-plan flows =", len(flows1265), "| new emergencies 2026 =", len(new_em))


if __name__ == "__main__":
    main()
