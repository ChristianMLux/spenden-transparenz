"""IATI via d-portal q.json (no key) + HDX 'iati-npl' CSV (no key) + IATI Registry CKAN (no key).

Questions: how many publishers/activities for Nepal, how many are Nepali
organisations (reporting_ref prefix 'NP-'), field fill rates, freshness,
anything touched since the 26.08.2026 flood, double-counting signals.
The Datastore API itself needs a subscription key -> documented, not used.
"""
import io
import zipfile
from collections import Counter, defaultdict

from common import FLOOD_DATE, dump_bytes, dump_json, fill_rate, log, out_dir, read_csv, session, summary

S = session(timeout=180)
SRC = "iati"
DPORTAL = "https://d-portal.org/q.json"
HDX_PKG = "https://data.humdata.org/api/3/action/package_show"
REGISTRY = "https://iatiregistry.org/api/3/action"


def dportal(**params):
    r = S.get(DPORTAL, params=params)
    r.raise_for_status()
    return r.json().get("rows", [])


def local_share(refs):
    c = Counter()
    for ref in refs:
        c["NP-" if (ref or "").upper().startswith("NP-") else "other"] += 1
    n = sum(c.values()) or 1
    return {"n": n, "np_prefixed": c["NP-"], "share_np": round(c["NP-"] / n, 3)}


def main():
    # --- d-portal: every active (status 2) activity with Nepal as recipient; aggregate offline ---
    acts = dportal(select="aid,reporting,reporting_ref,funder_ref,title,status_code,day_start,day_end,commitment,spend,flags,humanitarian",
                   **{"from": "act"}, country_code="NP", status_code="2", limit=50000)
    dump_json(SRC, "dportal_active_activities_np", acts)
    by_pub = Counter(a.get("reporting_ref") for a in acts)
    pub_names = {a.get("reporting_ref"): a.get("reporting") for a in acts}
    local = local_share(by_pub.keys())
    # activities that started on/after the flood (day_start = days since epoch)
    flood_day = (FLOOD_DATE.toordinal() - 719163)
    started_after = [a for a in acts if (a.get("day_start") or 0) >= flood_day]
    titles = defaultdict(set)
    for a in acts:
        titles[(a.get("title") or "").strip().lower()].add(a.get("reporting_ref"))
    dup_titles = {t: sorted(p) for t, p in titles.items() if t and len(p) > 1}
    humanitarian = sum(1 for a in acts if a.get("humanitarian") in (1, "1", True))

    # all activities (any status) started since 26.08.2026 — is anyone publishing about the flood yet?
    recent_any = dportal(select="aid,reporting,reporting_ref,title,status_code,day_start", **{"from": "act"}, country_code="NP", day_start_gteq=flood_day, limit=1000)
    dump_json(SRC, "dportal_started_since_flood_any_status", recent_any)

    # --- HDX: package metadata + both CSVs ---
    pkg = S.get(HDX_PKG, params={"id": "iati-npl"}).json()["result"]
    dump_json(SRC, "hdx_iati_npl_package", pkg)
    hdx_stats = {}
    for res in pkg.get("resources", []):
        if res.get("format", "").upper() != "CSV":
            continue
        raw = S.get(res["url"]).content
        name = "hdx_" + ("locations" if "location" in res.get("name", "").lower() and "no location" not in res.get("name", "").lower() else "activities") + ".csv"
        path = dump_bytes(SRC, name, raw)
        rows = read_csv(path)
        cols = list(rows[0].keys()) if rows else []
        fr = fill_rate(rows, cols)
        refs = [r.get("reporting_org_ref") or r.get("reporting-org-ref") or r.get("reporting_org_identifier") for r in rows]
        hdx_stats[name] = {
            "resource_name": res.get("name"), "last_modified": res.get("last_modified"), "rows": len(rows), "columns": cols,
            "fill_rate": fr, "local_share_by_row": local_share(refs) if any(refs) else None,
            "distinct_publishers": len(set(refs)) if any(refs) else None,
        }

    # --- IATI Registry (CKAN): how many publishers in total, how many datasets mention Nepal ---
    reg = {}
    try:
        orgs = S.get(f"{REGISTRY}/organization_list", params={"all_fields": True, "limit": 5000}).json()["result"]
        reg["publishers_total"] = len(orgs)
        np_orgs = [o for o in orgs if (o.get("publisher_country") or "").upper() == "NP" or (o.get("publisher_iati_id") or "").upper().startswith("NP-")]
        reg["publishers_np"] = [{"name": o.get("title"), "id": o.get("publisher_iati_id"), "org_type": o.get("publisher_organization_type")} for o in np_orgs]
        dump_json(SRC, "registry_publishers_np", np_orgs)
        ds = S.get(f"{REGISTRY}/package_search", params={"fq": "extras_country:NP", "rows": 0}).json()["result"]
        reg["datasets_country_NP"] = ds.get("count")
    except Exception as e:  # registry is best-effort
        reg["error"] = f"{type(e).__name__}: {e}"

    out = {
        "datastore_api": "needs free subscription key (401 without) - not used; d-portal + HDX cover the questions",
        "dportal_active_np": {
            "activities": len(acts), "publishers": len(by_pub), "humanitarian_flagged": humanitarian,
            "publisher_local_share": local, "top_publishers": [(pub_names[k], k, v) for k, v in by_pub.most_common(15)],
            "np_publishers": sorted({(pub_names[k], k) for k in by_pub if (k or "").upper().startswith("NP-")}),
            "started_on_or_after_flood": len(started_after), "duplicate_title_groups": len(dup_titles), "duplicate_title_examples": list(dup_titles.items())[:8],
            "field_fill_rate": fill_rate(acts, ["title", "day_start", "day_end", "commitment", "spend", "funder_ref"]),
        },
        "dportal_started_since_flood_any_status": len(recent_any),
        "hdx": hdx_stats,
        "registry": reg,
    }
    summary(SRC, out)
    log("IATI: active NP activities =", len(acts), "| publishers =", len(by_pub), "| NP-prefixed publishers =", local, "| started since flood =", len(recent_any))


if __name__ == "__main__":
    main()
