"""ProPublica Nonprofit Explorer API (free, no key). US orgs only.

Questions: how many 'nepal' orgs, which 990 fields are there per filing,
is an overhead/programme ratio derivable, how old is the newest filing.
"""
from collections import Counter

from common import dump_json, log, session, summary

S = session()
SRC = "propublica"
BASE = "https://projects.propublica.org/nonprofits/api/v2"
SAMPLE = ["America Nepal Medical Foundation", "Nepal Youth Foundation", "Himalayan Healthcare", "Nepal SEEDS", "Direct Relief"]
RATIO_FIELDS = ["totrevenue", "totfuncexpns", "totcntrbgfts", "totprgmrevnue", "compnsatncurrofcr", "othrsalwages", "totassetsend", "totliabend", "tax_prd_yr", "pdf_url"]


def search(q, page=0):
    r = S.get(f"{BASE}/search.json", params={"q": q, "page": page})
    r.raise_for_status()
    return r.json()


def main():
    first = search("nepal")
    total, per_page = first.get("total_results", 0), first.get("per_page") or len(first.get("organizations", []))
    orgs = list(first.get("organizations", []))
    for p in range(1, (total + per_page - 1) // per_page if per_page else 0):
        orgs.extend(search("nepal", p).get("organizations", []))
    dump_json(SRC, "search_nepal", orgs, {"total_results": total})
    states = Counter(o.get("state") for o in orgs)
    ntee = Counter(o.get("ntee_code") for o in orgs)

    samples = []
    for name in SAMPLE:
        hits = search(name).get("organizations", [])
        if not hits:
            samples.append({"query": name, "found": False})
            continue
        ein = hits[0]["ein"]
        r = S.get(f"{BASE}/organizations/{ein}.json")
        r.raise_for_status()
        org = r.json()
        dump_json(SRC, f"org_{ein}", org)
        fwd = org.get("filings_with_data", [])
        newest = fwd[0] if fwd else {}
        rev, exp = newest.get("totrevenue"), newest.get("totfuncexpns")
        samples.append({
            "query": name, "found": True, "name": org.get("organization", {}).get("name"), "ein": ein,
            "filings_with_data": len(fwd), "filings_without_data": len(org.get("filings_without_data", [])),
            "newest_tax_year": newest.get("tax_prd_yr"), "totrevenue": rev, "totfuncexpns": exp,
            "fields_present": [k for k in RATIO_FIELDS if newest.get(k) not in (None, "", 0)],
            "functional_expense_split_in_api": any(k in newest for k in ("prgmservicesexpenses", "mgmtgenexpns", "fundraisingexpns", "totprgmexpns")),
            "all_filing_keys": sorted(newest.keys())[:60],
        })

    out = {
        "search_nepal_total": total, "states_top": dict(states.most_common(8)), "ntee_top": dict(ntee.most_common(8)),
        "samples": samples,
        "note": "totrevenue/totfuncexpns come from the 990 header; programme/management/fundraising split (Part IX) is NOT in the API filing summary -> ratio only via the PDF/XML",
    }
    summary(SRC, out)
    log("ProPublica: nepal hits =", total, "| samples =", [(s.get("name"), s.get("newest_tax_year")) for s in samples])


if __name__ == "__main__":
    main()
