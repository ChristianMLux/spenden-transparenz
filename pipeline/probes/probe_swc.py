"""Nepal Social Welfare Council (swc.org.np). Live site unreachable from here on
28.08.2026 (timeouts). Fallback: Wayback Machine CDX index + latest snapshots
of the download / NGO-list pages, to learn what format the register data has.
"""
import re

import requests

from common import dump_bytes, dump_json, log, session, summary

S = session(timeout=45)
SRC = "swc"
LIVE = ["https://swc.org.np/", "http://swc.org.np/", "https://www.swc.org.np/", "http://www.swc.org.np/"]
CDX = "https://web.archive.org/cdx/search/cdx"
PAGES = ["swc.org.np/downloads", "swc.org.np/?page_id=47", "swc.org.np/pages/459", "swc.org.np/"]
LINK_RE = re.compile(r'href="([^"]+\.(?:pdf|xlsx?|csv|docx?))"', re.I)


def try_live():
    for u in LIVE:
        try:
            r = S.get(u, timeout=20)
            return {"url": u, "status": r.status_code, "len": len(r.content)}
        except requests.RequestException as e:
            continue
    return {"reachable": False}


def cdx(url_pattern, **kw):
    r = S.get(CDX, params={"url": url_pattern, "output": "json", "fl": "timestamp,original,statuscode,mimetype", "filter": "statuscode:200", "collapse": "urlkey", "limit": 3000, **kw})
    if r.status_code != 200 or not r.text.strip():
        return []
    rows = r.json()
    return [dict(zip(rows[0], row)) for row in rows[1:]]


def main():
    live = try_live()
    index = cdx("swc.org.np/*", **{"from": "2022"})
    dump_json(SRC, "wayback_cdx_index_since_2022", index)
    docs = [x for x in index if re.search(r"\.(pdf|xlsx?|csv|docx?)$", x["original"], re.I)]
    ngo_like = [x for x in index if re.search(r"ngo|ingo|affiliat|list|download|register", x["original"], re.I)]

    snapshots = {}
    for page in PAGES:
        hits = cdx(page, **{"from": "2023"})
        if not hits:
            snapshots[page] = {"snapshot": None}
            continue
        latest = sorted(hits, key=lambda x: x["timestamp"])[-1]
        wb = f"https://web.archive.org/web/{latest['timestamp']}/{latest['original']}"
        r = S.get(wb)
        name = re.sub(r"[^a-z0-9]+", "_", page.lower()).strip("_") + ".html"
        dump_bytes(SRC, name, r.content)
        html = r.text
        links = LINK_RE.findall(html)
        snapshots[page] = {"snapshot": wb, "status": r.status_code, "doc_links": links[:40], "n_doc_links": len(links),
                           "title": (re.search(r"<title>(.*?)</title>", html, re.I | re.S) or [None, None])[1]}

    out = {
        "live": live,
        "wayback_urls_since_2022": len(index), "wayback_document_urls": [x["original"] for x in docs][:60], "wayback_ngo_like_urls": [x["original"] for x in ngo_like][:60],
        "snapshots": snapshots,
        "structural_note": "SWC affiliation is voluntary for national NGOs (DAO registration is the legal minimum) -> SWC list is a subset by construction",
    }
    summary(SRC, out)
    log("SWC: live =", live, "| wayback urls =", len(index), "| docs =", len(docs))


if __name__ == "__main__":
    main()
