"""UK Charity Commission — bulk register extract (no key). API needs a free key (401 without).

Questions: how many Nepal-related charities, which financial fields exist,
how fresh, what the annual-return history gives for peer comparison.
Both extracts are downloaded once and indexed by registered_charity_number.
"""
import io
import json
import zipfile
from collections import Counter, defaultdict

from common import dump_bytes, dump_json, fill_rate, log, out_dir, session, summary

S = session(timeout=600)
SRC = "ukcc"
BLOB = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json"
MAIN = f"{BLOB}/publicextract.charity.zip"
ARH = f"{BLOB}/publicextract.charity_annual_return_history.zip"
KEYWORDS = ("nepal", "himalay", "sherpa", "gurkha", "gorkha", "everest")


def load_zip_json(url, name):
    cached = out_dir(SRC) / name
    if cached.exists():
        raw = cached.read_bytes()
    else:
        raw = S.get(url).content
        dump_bytes(SRC, name, raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        inner = z.namelist()[0]
        text = z.read(inner).decode("utf-8-sig")
    text = text.strip()
    return json.loads(text) if text.startswith("[") else [json.loads(l) for l in text.splitlines() if l.strip()]


def main():
    charities = load_zip_json(MAIN, "publicextract.charity.zip")
    cols = list(charities[0].keys())
    registered = [c for c in charities if (c.get("charity_registration_status") or "").lower() == "registered"]
    nepal = [c for c in registered if any(k in (c.get("charity_name") or "").lower() for k in KEYWORDS)]
    dump_json(SRC, "nepal_related_registered", nepal, {"keywords": KEYWORDS})

    arh = load_zip_json(ARH, "publicextract.charity_annual_return_history.zip")
    by_num = defaultdict(list)
    for r in arh:
        by_num[r.get("registered_charity_number")].append(r)
    nepal_nums = {c.get("registered_charity_number") for c in nepal}
    years_per_nepal = [len(by_num.get(n, [])) for n in nepal_nums]

    income_buckets = Counter()
    for c in nepal:
        inc = c.get("latest_income") or 0
        income_buckets["<10k" if inc < 1e4 else "<100k" if inc < 1e5 else "<1M" if inc < 1e6 else ">=1M"] += 1

    nepal_sorted = sorted(nepal, key=lambda c: c.get("latest_income") or 0, reverse=True)
    sample = []
    for c in nepal_sorted[:5] + nepal_sorted[len(nepal_sorted) // 2: len(nepal_sorted) // 2 + 2]:
        num = c.get("registered_charity_number")
        hist = sorted(by_num.get(num, []), key=lambda r: r.get("fin_period_end_date") or "")
        sample.append({
            "name": c.get("charity_name"), "number": num, "latest_income": c.get("latest_income"), "latest_expenditure": c.get("latest_expenditure"),
            "fin_year_end": c.get("latest_acc_fin_period_end_date"), "reporting_status": c.get("charity_reporting_status"),
            "activities": (c.get("charity_activities") or "")[:160], "history_years": len(hist),
            "history_fields": sorted(hist[-1].keys()) if hist else [],
            "register_url": f"https://register-of-charities.charitycommission.gov.uk/charity-search/-/charity-details/{num}",
        })

    out = {
        "api": "needs free subscription key (401 without); bulk extract used instead",
        "extract_rows_total": len(charities), "registered": len(registered), "columns": cols,
        "nepal_related_registered": len(nepal), "income_buckets": dict(income_buckets),
        "fill_rate_nepal": fill_rate(nepal, ["latest_income", "latest_expenditure", "latest_acc_fin_period_end_date", "charity_reporting_status", "charity_activities", "charity_contact_web", "charity_company_registration_number"]),
        "annual_return_history_rows": len(arh), "history_years_per_nepal_charity": {"min": min(years_per_nepal or [0]), "median": sorted(years_per_nepal)[len(years_per_nepal) // 2] if years_per_nepal else 0, "max": max(years_per_nepal or [0])},
        "samples": sample,
    }
    summary(SRC, out)
    log("UK CC: registered =", len(registered), "| nepal-related =", len(nepal), "| ARH rows =", len(arh))


if __name__ == "__main__":
    main()
