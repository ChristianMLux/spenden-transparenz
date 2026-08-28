"""UK Charity Commission Register API — needs UK_CHARITY_COMMISSION_API_KEY
(env / .env.spenden / AthenaRun/.env.platform). Header Ocp-Apim-Subscription-Key.

Question: what does the API add on top of the bulk extract (probe_ukcc.py)?
Candidates: area of operation (country list -> proper 'works in Nepal' filter
instead of name matching), financial history per year, trustees, accounts/
annual-return documents, policies, published reports. One call per endpoint
per sample charity; endpoints that 404 are recorded as unavailable.
"""
from collections import Counter

from common import dump_json, load_json, log, platform_key, session, summary

S = session(timeout=60)
SRC = "ukcc_api"
BASE = "https://api.charitycommission.gov.uk/register/api"
KEY = platform_key("UK_CHARITY_COMMISSION_API_KEY")
S.headers["Ocp-Apim-Subscription-Key"] = KEY
S.headers["Cache-Control"] = "no-cache"

ENDPOINTS = ["allcharitydetails", "charitydetails", "charityfinancialhistory", "charitytrusteeinformation", "charityareaofoperation",
             "charityaccountsandreturns", "charityaccountsandannualreturns", "charitypublishedreports", "charitypolicies",
             "charitygoverningdocument", "charityclassification", "charityregistrations", "charityeventhistory", "charityoverview"]


def get(path):
    r = S.get(f"{BASE}/{path}")
    try:
        body = r.json()
    except ValueError:
        body = r.text[:300]
    return r.status_code, body


def main():
    if not KEY:
        summary(SRC, {"status": "key missing"})
        log("UK_CHARITY_COMMISSION_API_KEY missing")
        return
    # sample = top-5 Nepal-related charities from the bulk extract + 2 small ones (same as probe_ukcc)
    nepal = load_json("ukcc", "nepal_related_registered")
    nepal.sort(key=lambda c: c.get("latest_income") or 0, reverse=True)
    sample = nepal[:5] + nepal[len(nepal) // 2: len(nepal) // 2 + 2]

    availability = {}
    per_charity = []
    for c in sample:
        num = c["registered_charity_number"]
        rec = {"name": c["charity_name"], "number": num, "endpoints": {}}
        for ep in ENDPOINTS:
            status, body = get(f"{ep}/{num}/0")
            availability.setdefault(ep, Counter())[status] += 1
            if status == 200:
                dump_json(SRC, f"{ep}_{num}", body)
                if isinstance(body, dict):
                    rec["endpoints"][ep] = {"keys": sorted(body.keys())[:40]}
                elif isinstance(body, list):
                    rec["endpoints"][ep] = {"rows": len(body), "keys": sorted(body[0].keys())[:40] if body and isinstance(body[0], dict) else None}
            else:
                rec["endpoints"][ep] = {"http": status}
        per_charity.append(rec)

    # the two questions that matter for the product
    first = per_charity[0]["number"]
    area = get(f"charityareaofoperation/{first}/0")[1]
    fin = get(f"charityfinancialhistory/{first}/0")[1]
    fin_sample = fin[:3] if isinstance(fin, list) else fin
    details = get(f"allcharitydetails/{first}/0")[1]
    details_keys = sorted(details.keys()) if isinstance(details, dict) else None

    # search endpoint: can we ask the register for 'Nepal' directly?
    s_status, s_body = get("charitysearch/nepal")
    search_hits = len(s_body) if isinstance(s_body, list) else None

    out = {
        "endpoint_availability": {ep: dict(cnt) for ep, cnt in availability.items()},
        "per_charity": per_charity,
        "allcharitydetails_keys": details_keys,
        "area_of_operation_sample": area if not isinstance(area, str) else area[:200],
        "financial_history_sample": fin_sample,
        "charitysearch_nepal": {"http": s_status, "hits": search_hits, "first": (s_body[:3] if isinstance(s_body, list) else s_body)},
        "verdict_inputs": {
            "area_of_operation_works": isinstance(area, (list, dict)),
            "financial_history_years": len(fin) if isinstance(fin, list) else None,
            "trustees_available": availability.get("charitytrusteeinformation", {}).get(200, 0) > 0,
            "accounts_docs_available": (availability.get("charityaccountsandreturns", {}).get(200, 0) + availability.get("charityaccountsandannualreturns", {}).get(200, 0)) > 0,
        },
    }
    summary(SRC, out)
    log("UK CC API:", out["endpoint_availability"], "| search nepal:", out["charitysearch_nepal"]["hits"])


if __name__ == "__main__":
    main()
