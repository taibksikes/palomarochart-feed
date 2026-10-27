#!/usr/bin/env python3
"""Rebuild the Paloma Rocha Pinterest product feed from the live Squarespace site.
Fetches every product page's ?format=json payload and writes feed.csv with the
columns Pinterest catalogs require."""
import json, re, csv, sys, time, urllib.request, html as h
from concurrent.futures import ThreadPoolExecutor

SITE = "https://palomarochart.com"
UA = {"User-Agent": "Mozilla/5.0"}

def get_json(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def fetch(url):
    for attempt in range(3):
        try:
            return url, get_json(url + "?format=json"), None
        except Exception as e:
            if attempt == 2:
                return url, None, str(e)[:80]
            time.sleep(4)

def desc(item):
    t = item.get("excerpt") or item.get("body") or ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = h.unescape(t)
    return re.sub(r"\s+", " ", t).strip()[:900]

def main():
    req = urllib.request.Request(SITE + "/sitemap.xml", headers=UA)
    xml = urllib.request.urlopen(req, timeout=60).read().decode()
    locs = sorted(set(re.findall(r"<loc>([^<]*/p/[^<]*)</loc>", xml)))
    print(f"product urls: {len(locs)}", flush=True)
    rows, problems = [], []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for url, d, err in ex.map(fetch, locs):
            if err:
                problems.append((url, err)); continue
            item = d.get("item", {})
            vs = item.get("structuredContent", {}).get("variants", [])
            if not vs:
                problems.append((url, "no variants")); continue
            v = vs[0]
            pm = v.get("priceMoney") or {}
            cur = pm.get("currency") or "MXN"
            val = pm.get("value")
            if val in (None, "0.00") and v.get("price"):
                val = f"{v['price']/100:.2f}"
            qty = v.get("qtyInStock")
            avail = "in stock" if (v.get("unlimited") or qty is None or qty > 0) else "out of stock"
            rows.append({
                "id": v.get("sku") or item.get("id"),
                "title": (item.get("title") or "").strip(),
                "description": desc(item),
                "link": SITE + (item.get("fullUrl") or ""),
                "image_link": item.get("assetUrl", ""),
                "price": f"{val} {cur}" if val else "",
                "availability": avail,
                "brand": "Paloma Rocha",
                "product_type": "Available Works",
                "condition": "new",
                "google_product_category": "Home & Garden > Decor > Artwork > Paintings",
            })
    rows.sort(key=lambda r: r["link"])
    if problems:
        print("PROBLEMS:", problems)
    if len(rows) < 40:
        print(f"ABORT: only {len(rows)} rows, keeping previous feed")
        sys.exit(1)
    fields = ["id","title","description","link","image_link","price","availability","brand","product_type","condition","google_product_category"]
    with open("feed.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"feed.csv written: {len(rows)} rows")

if __name__ == "__main__":
    main()
