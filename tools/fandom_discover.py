"""Temporary: dump Big Brother Wiki (Fandom) pages so the parser can be written
against real markup. Run by .github/workflows/fandom-discover.yml; removed after."""
import json
import sys
import time
from pathlib import Path

import requests

API = "https://bigbrother.fandom.com/api.php"
UA = ("BigBrotherWeekGrid/0.1 "
      "(https://github.com/christopherbholland/BigBrotherDataFromWiki; batch visualization pipeline)")
OUT = Path("cache/fandom_discovery")
S = requests.Session()
S.headers["User-Agent"] = UA


def get(**params):
    params.update(format="json", formatversion="2")
    for attempt in range(4):
        r = S.get(API, params=params, timeout=60)
        if r.status_code == 200:
            time.sleep(0.3)
            return r.json()
        print("HTTP", r.status_code, params, file=sys.stderr)
        time.sleep(2 ** attempt)
    r.raise_for_status()


def safe(title):
    return "".join(c if c.isalnum() or c in "-_()" else "_" for c in title)


def parse(title, sub):
    d = get(action="parse", page=title, redirects=1,
            prop="text|wikitext|revid|links|categories|templates|sections|displaytitle")
    if "error" in d:
        print("ERROR", title, d["error"], file=sys.stderr)
        return None
    p = d["parse"]
    (OUT / sub).mkdir(parents=True, exist_ok=True)
    base = OUT / sub / safe(p["title"])
    base.with_suffix(".html").write_text(p["text"], encoding="utf-8")
    base.with_suffix(".wikitext").write_text(p["wikitext"], encoding="utf-8")
    meta = {k: p.get(k) for k in ("title", "revid", "categories", "sections")}
    meta["links"] = [l["title"] for l in p.get("links", []) if l.get("ns") == 0 and l.get("exists")]
    meta["templates"] = [t["title"] for t in p.get("templates", [])]
    base.with_suffix(".meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return meta


def linked_heads(titles):
    """Categories + first 4000 chars of wikitext for each linked page."""
    rows = {}
    titles = sorted(set(titles))
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        cont = {}
        while True:
            d = get(action="query", titles="|".join(chunk), redirects=1, prop="revisions|categories",
                    rvprop="content|ids", rvslots="main", cllimit="max", **cont)
            for pg in d["query"].get("pages", []):
                row = rows.setdefault(pg["title"], {"categories": []})
                row["categories"] += [c["title"] for c in pg.get("categories", [])]
                if pg.get("revisions"):
                    rev = pg["revisions"][0]
                    row["revid"] = rev["revid"]
                    row["head"] = rev["slots"]["main"]["content"][:4000]
            for rd in d["query"].get("redirects", []):
                rows.setdefault("_redirects", {})[rd["from"]] = rd["to"]
            if "continue" not in d:
                break
            cont = d["continue"]
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    si = get(action="query", meta="siteinfo", siprop="general|statistics|rightsinfo")
    (OUT / "siteinfo.json").write_text(json.dumps(si, indent=1), encoding="utf-8")
    all_links = set()
    for n in range(21, 29):
        meta = parse(f"Big Brother {n} (US)", "seasons")
        if meta:
            print(f"BB{n}: rev {meta['revid']} links {len(meta['links'])}")
            all_links.update(meta["links"])
        cm = get(action="query", list="categorymembers", cmtitle=f"Category:Big Brother {n} (US)",
                 cmlimit="max")
        (OUT / "seasons" / f"category_bb{n}.json").write_text(
            json.dumps([m["title"] for m in cm["query"]["categorymembers"]], indent=1, ensure_ascii=False),
            encoding="utf-8")
    for extra in ["List of Big Brother (US) Contestants/Main Series", "Have-Not", "The Wall",
                  "Chelsie Baham", "Final Three (BB26)"]:
        parse(extra, "extra")
    heads = linked_heads(all_links)
    (OUT / "linked_heads.json").write_text(json.dumps(heads, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(heads)} linked pages")


if __name__ == "__main__":
    main()
