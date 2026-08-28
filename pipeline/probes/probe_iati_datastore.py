"""IATI Datastore API (api.iatistandard.org) — needs IATI_EXPLORATORY_KEY
(env or ../AthenaRun/.env.platform). Answers what d-portal could not:
humanitarian flag, participating orgs (implementers, not just publishers),
transaction level (commitment vs disbursement), last_updated since the flood.
Solr-style: one request per question, facets instead of row dumps.
"""
from collections import Counter

from common import FLOOD_DATE, dump_json, log, platform_key, session, summary

S = session(timeout=120)
SRC = "iati_datastore"
BASE = "https://api.iatistandard.org/datastore"
KEY = platform_key("IATI_EXPLORATORY_KEY")
S.headers["Ocp-Apim-Subscription-Key"] = KEY


def solr(collection: str, name: str, **params):
    q = {"rows": 0, "wt": "json", **params}
    r = S.get(f"{BASE}/{collection}/select", params=q)
    if r.status_code != 200:
        log(f"  {name}: HTTP {r.status_code} {r.text[:160]}")
        return {"error": r.status_code, "body": r.text[:300]}
    d = r.json()
    dump_json(SRC, name, d, {"params": q})
    return d


def facet_counts(d, field):
    ff = (d.get("facet_counts") or {}).get("facet_fields", {}).get(field, [])
    return dict(zip(ff[::2], ff[1::2]))


def main():
    if not KEY:
        log("IATI_EXPLORATORY_KEY missing (env or ../AthenaRun/.env.platform) -> nothing to do")
        summary(SRC, {"status": "key missing", "note": "add IATI_EXPLORATORY_KEY=<key> to AthenaRun/.env.platform and re-run"})
        return

    np_active = "recipient_country_code:NP AND activity_status_code:2"
    out = {}

    # 1. activities for Nepal, active; humanitarian flag; publishers
    d = solr("activity", "np_active_humanitarian", q=np_active, facet="true",
             **{"facet.field": ["humanitarian", "reporting_org_type", "participating_org_type", "participating_org_role"], "facet.limit": 50})
    out["np_active_activities"] = d.get("response", {}).get("numFound")
    out["humanitarian_flag"] = facet_counts(d, "humanitarian")
    out["reporting_org_type"] = facet_counts(d, "reporting_org_type")
    out["participating_org_type"] = facet_counts(d, "participating_org_type")
    out["participating_org_role"] = facet_counts(d, "participating_org_role")
    out["org_type_codes"] = "10 Government, 15 Other public sector, 21 INGO, 22 National NGO, 23 Regional NGO, 24 Partner-country NGO, 30 PPP, 40 Multilateral, 60 Foundation, 70 Private sector, 80 Academic; roles 1 funding, 2 accountable, 3 extending, 4 implementing"

    # 2. participating orgs (implementers, role 4) — how many NP-prefixed refs?
    d = solr("activity", "np_participating_orgs", q=np_active, facet="true",
             **{"facet.field": ["participating_org_ref"], "facet.limit": 3000, "facet.mincount": 1})
    parts = facet_counts(d, "participating_org_ref")
    np_refs = {k: v for k, v in parts.items() if k.upper().startswith("NP-")}
    out["participating_org_refs"] = {"distinct": len(parts), "np_prefixed": len(np_refs), "top_np": sorted(np_refs.items(), key=lambda x: -x[1])[:25]}

    # 2b. national NGOs (type 22) as participating orgs: which refs, how many activities
    d = solr("activity", "np_participating_national_ngos", q=np_active + " AND participating_org_type:22", facet="true",
             **{"facet.field": ["participating_org_ref"], "facet.limit": 3000, "facet.mincount": 1})
    refs22 = facet_counts(d, "participating_org_ref")
    out["activities_with_national_ngo_participant"] = d.get("response", {}).get("numFound")
    out["national_ngo_refs"] = {"distinct_refs_on_those_activities": len(refs22), "np_prefixed": sorted(((k, v) for k, v in refs22.items() if k.upper().startswith("NP-")), key=lambda x: -x[1])[:30]}

    # 3. anything updated since the flood?
    d = solr("activity", "np_updated_since_flood", q=f"recipient_country_code:NP AND last_updated_datetime:[{FLOOD_DATE.isoformat()}T00:00:00Z TO *]",
             rows=50, fl="iati_identifier,reporting_org_narrative,title_narrative,last_updated_datetime,humanitarian,activity_status_code")
    docs = d.get("response", {}).get("docs", [])
    out["updated_since_flood"] = {"n": d.get("response", {}).get("numFound"), "sample": [(x.get("reporting_org_narrative"), (x.get("title_narrative") or [""])[0][:70], x.get("last_updated_datetime")) for x in docs[:15]]}
    hum_recent = [x for x in docs if x.get("humanitarian") in (True, "1", 1)]
    out["updated_since_flood_humanitarian"] = len(hum_recent)

    # 4. transactions: commitments vs disbursements to Nepal, 2026
    d = solr("transaction", "np_transactions_2026", q="transaction_recipient_country_code:NP AND transaction_transaction_date_iso_date:[2026-01-01T00:00:00Z TO *]",
             facet="true", **{"facet.field": ["transaction_transaction_type_code", "transaction_provider_org_ref", "transaction_receiver_org_ref", "transaction_humanitarian"], "facet.limit": 40},
             rows=5, fl="iati_identifier,transaction_type,transaction_value,transaction_transaction_date_iso_date,transaction_provider_org_narrative,transaction_receiver_org_narrative")
    out["transactions_2026"] = {"n": d.get("response", {}).get("numFound"), "by_type": facet_counts(d, "transaction_transaction_type_code"), "humanitarian": facet_counts(d, "transaction_humanitarian"),
                                "top_receivers": list(facet_counts(d, "transaction_receiver_org_ref").items())[:15],
                                "sample": d.get("response", {}).get("docs", [])[:5],
                                "type_codes": "1 incoming funds, 2 outgoing commitment, 3 disbursement, 4 expenditure, 11 incoming commitment"}

    # 5. transactions dated on/after the flood
    d = solr("transaction", "np_transactions_since_flood", q=f"transaction_recipient_country_code:NP AND transaction_transaction_date_iso_date:[{FLOOD_DATE.isoformat()}T00:00:00Z TO *]",
             rows=20, fl="iati_identifier,transaction_type,transaction_value,transaction_transaction_date_iso_date,transaction_provider_org_narrative,transaction_receiver_org_narrative,reporting_org_narrative")
    out["transactions_since_flood"] = {"n": d.get("response", {}).get("numFound"), "sample": d.get("response", {}).get("docs", [])[:10]}

    summary(SRC, out)
    log("IATI datastore:", {k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk in ("n", "distinct", "np_prefixed")}) for k, v in out.items() if k != "reporting_org_type"})


if __name__ == "__main__":
    main()
