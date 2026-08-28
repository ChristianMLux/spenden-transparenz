"""UK Charity Commission — the other bulk extracts (no key): area of operation,
annual return Part B (expenditure split), trustees, classification.

Question: how many registered charities really operate in Nepal (area of
operation, not name match), and for how many is a programme ratio derivable
from Part B. Everything indexed once by registered_charity_number.
"""
import io
import json
import zipfile
from collections import defaultdict

from common import dump_bytes, dump_json, log, out_dir, session, summary

S = session(timeout=600)
SRC = "ukcc"
BLOB = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json"


def load_zip_json(name):
    cached = out_dir(SRC) / name
    raw = cached.read_bytes() if cached.exists() else S.get(f"{BLOB}/{name}").content
    if not cached.exists():
        dump_bytes(SRC, name, raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode("utf-8-sig").strip()
    return json.loads(text) if text.startswith("[") else [json.loads(l) for l in text.splitlines() if l.strip()]


def main():
    charities = {c["registered_charity_number"]: c for c in load_zip_json("publicextract.charity.zip") if (c.get("charity_registration_status") or "").lower() == "registered" and c.get("linked_charity_number") in (0, None, "0")}
    aoo = load_zip_json("publicextract.charity_area_of_operation.zip")
    nepal_nums = {r["registered_charity_number"] for r in aoo if (r.get("geographic_area_description") or r.get("area_of_operation") or "").strip().lower() == "nepal"}
    nepal = [charities[n] for n in nepal_nums if n in charities]
    partb = load_zip_json("publicextract.charity_annual_return_partb.zip")
    pb = defaultdict(list)
    for r in partb:
        pb[r["registered_charity_number"]].append(r)
    pb_cols = sorted(partb[0].keys()) if partb else []
    exp_col = next((c for c in pb_cols if c.startswith("expenditure") and "charitable" in c), None)
    tot_col = next((c for c in pb_cols if c in ("exp_total", "total_expenditure", "expenditure_total")), None) or next((c for c in pb_cols if c.startswith("exp") and "total" in c), None)
    with_split, ratios = 0, []
    for n in nepal_nums:
        rows = sorted(pb.get(n, []), key=lambda r: r.get("fin_period_end_date") or "")
        if rows and exp_col and tot_col and rows[-1].get(exp_col) is not None and rows[-1].get(tot_col):
            with_split += 1
            ratios.append(round(rows[-1][exp_col] / rows[-1][tot_col], 3))
    ratios.sort()
    dump_json(SRC, "nepal_by_area_of_operation", nepal, {"n": len(nepal), "source": "publicextract.charity_area_of_operation.zip"})
    inc = sorted((c.get("latest_income") or 0) for c in nepal)
    out = {
        "registered_main_charities": len(charities),
        "area_of_operation_rows": len(aoo), "aoo_columns": sorted(aoo[0].keys()) if aoo else [],
        "nepal_by_area_of_operation": len(nepal),
        "nepal_income_median": inc[len(inc) // 2] if inc else None, "nepal_income_over_1M": sum(1 for x in inc if x >= 1e6),
        "partb_rows": len(partb), "partb_columns": pb_cols, "partb_exp_col": exp_col, "partb_total_col": tot_col,
        "nepal_with_expenditure_split": with_split,
        "program_ratio_distribution": {"n": len(ratios), "p10": ratios[len(ratios) // 10] if ratios else None, "median": ratios[len(ratios) // 2] if ratios else None, "p90": ratios[int(len(ratios) * 0.9)] if ratios else None},
        "note": "Part B is only required above the income threshold (GBP 500k) -> split exists for larger charities only",
    }
    summary(SRC + "_bulk_extra", out)
    log("UK CC bulk extra: Nepal by area of operation =", len(nepal), "| with Part-B split =", with_split, "| ratio median =", out["program_ratio_distribution"]["median"])


if __name__ == "__main__":
    main()
