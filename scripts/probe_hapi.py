"""HDX HAPI (hapi.humdata.org). Self-generated app_identifier, no registration.

Questions: org taxonomy (local vs international), operational presence (3W)
for Nepal, funding + affected-people coverage.
"""
import base64
from collections import Counter

from common import dump_json, log, session, summary

S = session()
SRC = "hapi"
BASE = "https://hapi.humdata.org/api/v2"
IDENT = base64.b64encode(b"spenden-transparenz-research:chris.lux.st@gmail.com").decode()


def get(path, **params):
    rows, offset = [], 0
    while True:
        r = S.get(f"{BASE}/{path}", params={"app_identifier": IDENT, "limit": 1000, "offset": offset, **params})
        if r.status_code != 200:
            return {"error": r.status_code, "body": r.text[:200]}
        data = r.json().get("data", [])
        rows.extend(data)
        if len(data) < 1000:
            return rows
        offset += 1000


def main():
    orgs = get("metadata/org")
    dump_json(SRC, "metadata_org", orgs)
    org_types = Counter(o.get("org_type_description") for o in orgs) if isinstance(orgs, list) else orgs

    probes = {
        "operational_presence_NPL": get("coordination-context/operational-presence", location_code="NPL"),
        "funding_NPL": get("coordination-context/funding", location_code="NPL"),
        "humanitarian_needs_NPL": get("affected-people/humanitarian-needs", location_code="NPL"),
        "idps_NPL": get("affected-people/idps", location_code="NPL"),
        "admin1_NPL": get("metadata/admin1", location_code="NPL"),
        "admin2_NPL": get("metadata/admin2", location_code="NPL"),
        "data_availability_NPL": get("metadata/data-availability", location_code="NPL"),
    }
    for k, v in probes.items():
        dump_json(SRC, k, v)

    def n(v):
        return len(v) if isinstance(v, list) else v

    out = {
        "app_identifier": "base64('appname:email'), self-generated, works without registration",
        "org_taxonomy_counts": dict(org_types.most_common()) if isinstance(org_types, Counter) else org_types,
        "orgs_total": len(orgs) if isinstance(orgs, list) else None,
        "npl_rows": {k: n(v) for k, v in probes.items()},
        "funding_sample": probes["funding_NPL"][:3] if isinstance(probes["funding_NPL"], list) else None,
        "data_availability_NPL": probes["data_availability_NPL"] if isinstance(probes["data_availability_NPL"], list) else None,
    }
    summary(SRC, out)
    log("HAPI:", out["npl_rows"])


if __name__ == "__main__":
    main()
