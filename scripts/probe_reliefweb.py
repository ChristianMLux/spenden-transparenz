"""ReliefWeb WITHOUT the API.

API v1 is gone (410); v2 requires an approved appname that ReliefWeb only issues
to organisations with an official e-mail domain (403 otherwise). The website
itself is enough for our questions:

  1. country page  /country/npl                  -> current disaster pages
  2. disaster page /disaster/<glide-slug>        -> disaster id  D<id>
  3. listing       /updates?advanced-search=(D<id>)&page=N   (20 per page, paginate until empty)
     per article: title, url, format, source(s), date            <- structured, no report fetch needed
  4. report page   /report/<country>/<slug>      -> full text for extraction
  5. RSS           /updates/rss.xml?advanced-search=(PC168)     <- freshness, capped at 20 items

Nepal country id = PC168. Disaster id discovered from the disaster page.
"""
import html as htmlmod
import re
import xml.etree.ElementTree as ET

from common import dump_bytes, dump_json, log, session, summary

S = session(timeout=45)
S.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) spenden-transparenz-research/0.1"
SRC = "reliefweb"
API = "https://api.reliefweb.int/v2/reports"
BASE = "https://reliefweb.int"
COUNTRY_ID = "PC168"  # Nepal
TAG = re.compile(r"<[^>]+>")
REPORT_LINK = re.compile(r'href="((?:https://reliefweb\.int)?/report/[^"#?]+)"')
ARTICLE = re.compile(r"<article[^>]*>(.*?)</article>", re.S)
FLOOD_WORDS = ("flood", "trishuli", "rasuwa", "nuwakot", "glacial", "glof", "flash", "landslide")


def strip(t):
    return htmlmod.unescape(TAG.sub(" ", t or "")).strip()


def absolute(u):
    return u if u.startswith("http") else BASE + u


def api_probe():
    r = S.post(API, params={"appname": "spenden-transparenz-research"}, json={"limit": 1, "filter": {"field": "country.iso3", "value": "npl"}})
    return {"status": r.status_code, "body": r.text[:200]}


def rss_items(advanced_search=f"({COUNTRY_ID})"):
    r = S.get(f"{BASE}/updates/rss.xml", params={"advanced-search": advanced_search})
    dump_bytes(SRC, "rss_nepal.xml", r.content)
    if r.status_code != 200:
        return [], r.status_code
    items = []
    for it in ET.fromstring(r.content).iter("item"):
        g = lambda k: (it.findtext(k) or "").strip()
        items.append({"title": g("title"), "link": g("link"), "pubDate": g("pubDate"), "description": strip(g("description"))[:300]})
    return items, r.status_code


def current_disasters():
    """Disaster pages linked from the country page + their D<id> for the updates listing."""
    r = S.get(f"{BASE}/country/npl")
    dump_bytes(SRC, "country_npl.html", r.content)
    pages = list(dict.fromkeys(re.findall(r'href="(https://reliefweb\.int/disaster/[^"#?]+)"', r.text)))
    out = []
    for url in pages:
        h = S.get(url).text
        m = re.search(r"%28D(\d+)%29|\(D(\d+)\)", h)
        title = strip((re.search(r"<title>(.*?)</title>", h, re.S) or [None, ""])[1]).replace(" | ReliefWeb", "")
        out.append({"url": url, "title": title, "disaster_id": (m.group(1) or m.group(2)) if m else None})
    return out, r.status_code


def listing(advanced_search, max_pages=50):
    """Paginate /updates for one advanced-search expression; parse structured metadata per article."""
    rows, total = [], None
    for page in range(max_pages):
        r = S.get(f"{BASE}/updates", params={"advanced-search": advanced_search, "page": page})
        if r.status_code != 200:
            break
        if total is None:
            m = re.search(r"([\d,\.]+)\s*results", TAG.sub(" ", r.text))
            total = int(m.group(1).replace(",", "").replace(".", "")) if m else None
        arts = ARTICLE.findall(r.text)
        if not arts:
            break
        for a in arts:
            link = REPORT_LINK.search(a)
            if not link:
                continue
            t = re.search(r'rw-river-article__title[^>]*>\s*<a[^>]*>(.*?)</a>', a, re.S)
            dd = [strip(x) for x in re.findall(r"<dd[^>]*>(.*?)</dd>", a, re.S)]
            tm = re.search(r'datetime="([^"]+)"', a)
            rows.append({"url": absolute(link.group(1)), "title": strip(t.group(1)) if t else None,
                         "format": dd[0] if dd else None, "sources": dd[1:-2] if len(dd) > 3 else dd[1:2], "date": tm.group(1) if tm else None})
    return {k: v for k, v in {r["url"]: r for r in rows}.items()}, total  # dedupe by url, keep order


def fetch_report(url):
    r = S.get(url)
    if r.status_code != 200:
        return {"url": url, "status": r.status_code}
    h = r.text
    m = lambda pat: (re.search(pat, h, re.I | re.S) or [None, None])[1]
    body = m(r'<div[^>]+class="[^"]*rw-report__content[^"]*"[^>]*>(.*?)</div>\s*(?:<footer|<section|<aside)')
    text = strip(body) if body else strip(re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", h, flags=re.I | re.S))[:8000]
    return {"url": url, "status": 200, "title": strip(m(r"<h1[^>]*>(.*?)</h1>")), "date": m(r'<time[^>]*datetime="([^"]+)"'), "text": text[:8000], "text_len": len(text)}


def main():
    api = api_probe()
    items, rss_status = rss_items()
    dump_json(SRC, "rss_items", items, {"http": rss_status, "advanced_search": f"({COUNTRY_ID})"})

    disasters, page_status = current_disasters()
    dump_json(SRC, "disasters_current", disasters)
    flood = next((d for d in disasters if d["disaster_id"] and any(w in d["title"].lower() for w in FLOOD_WORDS)), None)

    flood_updates, flood_total = ({}, None)
    if flood:
        flood_updates, flood_total = listing(f"(D{flood['disaster_id']})")
        dump_json(SRC, "disaster_updates", list(flood_updates.values()), {"disaster": flood, "listing_total": flood_total})

    country_page0, country_total = listing(f"({COUNTRY_ID})", max_pages=1)
    dump_json(SRC, "country_updates_page0", list(country_page0.values()), {"listing_total": country_total})

    # full text for the flood updates (extraction input); listing metadata already structured
    reports = [fetch_report(u) | {"format": row["format"], "sources": row["sources"]} for u, row in list(flood_updates.items())[:40]]
    dump_json(SRC, "reports_sample", reports)
    ok = [r for r in reports if r.get("status") == 200]

    fmt = {}
    src = {}
    for row in flood_updates.values():
        fmt[row["format"]] = fmt.get(row["format"], 0) + 1
        for s in row["sources"]:
            src[s] = src.get(s, 0) + 1
    out = {
        "api_v2": api,
        "no_api_path": "country page -> disaster page -> D<id> -> /updates?advanced-search=(D<id>)&page=N (20/page) -> report pages",
        "rss": {"http": rss_status, "items": len(items), "cap": 20},
        "disasters_current": disasters,
        "flood_disaster": flood,
        "flood_updates": {"listing_total": flood_total, "distinct": len(flood_updates), "by_format": fmt, "by_source": dict(sorted(src.items(), key=lambda x: -x[1])),
                          "date_range": [min((r["date"] or "") for r in flood_updates.values()), max((r["date"] or "") for r in flood_updates.values())] if flood_updates else None},
        "country_listing_total": country_total,
        "reports_fetched": len(ok), "reports_failed": len(reports) - len(ok),
        "field_fill_listing": {k: round(sum(1 for r in flood_updates.values() if r.get(k)) / max(len(flood_updates), 1), 2) for k in ("title", "format", "sources", "date")},
        "sample_titles": [((r.get("date") or "")[:10], r.get("sources"), r.get("title")) for r in ok[:40]],
    }
    summary(SRC, out)
    log("ReliefWeb: api", api["status"], "| disaster", flood and flood["disaster_id"], "| flood updates", len(flood_updates), "/", flood_total, "| country total", country_total, "| reports ok", len(ok))


if __name__ == "__main__":
    main()
