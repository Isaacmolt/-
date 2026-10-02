#!/usr/bin/env python3
"""
蝦皮分潤 — 連結整理器 & 好物清單頁產生器

做三件事：
1. 把 products.csv 裡的蝦皮商品網址清成標準格式（去掉追蹤參數、抓出 shopid/itemid）
2. 依 config 的 sub_id_pattern 幫每個「商品 × 平台」產生 sub_id，輸出一張「貼到後台用」的批次表
   → shopee-affiliate/reports/link-batch.csv
3. 用已填好 affiliate_link 的商品，產生手機版好物清單頁（放在 Threads/IG 個人檔案連結）
   → shopee-affiliate/linkpage/index.html

蝦皮分潤的短連結（s.shopee.tw/xxx）只能從官方後台產生，沒有公開 API，
所以流程是：跑這支 → 打開 link-batch.csv → 到後台逐一貼網址＋sub_id → 把短連結填回 products.csv 的 affiliate_link → 再跑一次。

用法：
    python scripts/shopee_link_builder.py                  # 產生批次表 + 清單頁（只放有分潤連結的商品）
    python scripts/shopee_link_builder.py --include-pending  # 清單頁連沒分潤連結的商品也放（用原始網址）
"""

import argparse
import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
MODULE_DIR = BASE_DIR / "shopee-affiliate"
PRODUCTS_PATH = MODULE_DIR / "products.csv"
CONFIG_PATH = MODULE_DIR / "config.json"
CONFIG_EXAMPLE_PATH = MODULE_DIR / "config.example.json"
BATCH_PATH = MODULE_DIR / "reports" / "link-batch.csv"
LINKPAGE_PATH = MODULE_DIR / "linkpage" / "index.html"

# 蝦皮商品網址的兩種常見格式
#   https://shopee.tw/product/123456/7891011
#   https://shopee.tw/商品名稱-i.123456.7891011?sp_atk=...
RE_PRODUCT_PATH = re.compile(r"/product/(\d+)/(\d+)")
RE_I_FORMAT = re.compile(r"-i\.(\d+)\.(\d+)")
RE_PLACEHOLDER = re.compile(r"SHOPID|ITEMID", re.IGNORECASE)
RE_SUB_ID_OK = re.compile(r"^[a-z0-9_]{1,50}$")


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_source"] = path.name
    return cfg


def load_products():
    with open(PRODUCTS_PATH, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_shopee_url(url):
    """回傳 (shopid, itemid, canonical_url, status)。status: ok / placeholder / short / unknown"""
    url = (url or "").strip()
    if not url:
        return None, None, "", "empty"
    if RE_PLACEHOLDER.search(url):
        return None, None, url, "placeholder"
    host = urlparse(url).netloc.lower()
    if host in ("s.shopee.tw", "shp.ee", "shope.ee"):
        return None, None, url, "short"
    m = RE_PRODUCT_PATH.search(url) or RE_I_FORMAT.search(url)
    if m:
        shopid, itemid = m.group(1), m.group(2)
        return shopid, itemid, f"https://shopee.tw/product/{shopid}/{itemid}", "ok"
    return None, None, url, "unknown"


def make_sub_id(pattern, platform_code, product, yyyymm):
    sub_id = pattern.format(
        platform=platform_code,
        niche=product["niche"],
        yyyymm=yyyymm,
        product_id=product["id"],
    ).lower()
    sub_id = re.sub(r"[^a-z0-9_]", "_", sub_id)
    if not RE_SUB_ID_OK.match(sub_id):
        raise ValueError(f"sub_id 不合法（只能英數底線，50 字內）：{sub_id}")
    return sub_id


def write_batch(products, cfg):
    yyyymm = datetime.now().strftime("%Y%m")
    pattern = cfg["sub_id_pattern"]
    platforms = [(k, v["code"]) for k, v in cfg["platforms"].items() if v.get("enabled")]
    BATCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with open(BATCH_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "name", "niche", "url_status", "canonical_url", "platform", "sub_id", "affiliate_link_填回來", "備註"])
        for p in products:
            shopid, itemid, canonical, status = parse_shopee_url(p["shopee_url"])
            note = {
                "ok": "",
                "placeholder": "⚠️ 範例網址，請先換成真實商品網址",
                "short": "已是短連結，直接貼後台即可",
                "unknown": "⚠️ 看不懂的網址格式",
                "empty": "⚠️ 沒填網址",
            }[status]
            for _, code in platforms:
                w.writerow([p["id"], p["name"], p["niche"], status, canonical, code,
                            make_sub_id(pattern, code, p, yyyymm), p.get("affiliate_link", ""), note])
                rows += 1
    return rows


# ── 好物清單頁 ──────────────────────────────────────────────────────

LINKPAGE_CSS = """
:root{--bg:#faf7f2;--card:#fff;--text:#1a1a1a;--muted:#6b6b6b;--accent:#ee4d2d;--accent-2:#2d5f2d;--line:#eee}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--card:#1f1f1f;--text:#f2f2f2;--muted:#a3a3a3;--line:#2c2c2c}}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,"PingFang TC","Noto Sans TC",system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.wrap{max-width:560px;margin:0 auto;padding:32px 16px 64px}
header{text-align:center;margin-bottom:28px}header h1{font-size:1.5rem;margin:0 0 4px}header p{margin:0;color:var(--muted);font-size:.95rem}
.disclosure{font-size:.8rem;color:var(--muted);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:16px 0 24px}
h2{font-size:1.05rem;margin:28px 0 12px;padding-left:10px;border-left:4px solid var(--accent-2)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin-bottom:12px}
.card .top{display:flex;justify-content:space-between;gap:12px;align-items:baseline}
.card h3{font-size:1rem;margin:0}.price{color:var(--accent);font-weight:700;white-space:nowrap}
.card ul{margin:8px 0 12px;padding-left:18px;color:var(--muted);font-size:.9rem}.card li{margin:2px 0}
.btn{display:block;text-align:center;background:var(--accent);color:#fff;text-decoration:none;font-weight:700;padding:12px;border-radius:12px}
.btn.pending{background:var(--muted)}
.tag{font-size:.75rem;color:var(--muted)}
footer{text-align:center;color:var(--muted);font-size:.8rem;margin-top:40px}
"""


def build_linkpage(products, cfg, include_pending=False):
    brand = cfg["brand"]
    title = cfg.get("linkpage", {}).get("title", brand["account_name"])
    # 依利基分組，保留 products.csv 的順序
    groups = {}
    niche_labels = {}
    try:
        niches = json.load(open(MODULE_DIR / "niches.json", encoding="utf-8"))["niches"]
        niche_labels = {n["id"]: n["name"] for n in niches}
    except Exception:
        pass

    shown = 0
    for p in products:
        link = (p.get("affiliate_link") or "").strip()
        _, _, canonical, status = parse_shopee_url(p["shopee_url"])
        if not link:
            if not include_pending or status == "placeholder":
                continue
            link = canonical
            pending = True
        else:
            pending = False
        groups.setdefault(p["niche"], []).append((p, link, pending))
        shown += 1

    parts = [
        "<!DOCTYPE html>", '<html lang="zh-Hant">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(title)}</title>",
        f'<meta name="description" content="{html.escape(brand["tagline"])}">',
        f"<style>{LINKPAGE_CSS}</style>", "</head>", "<body>", '<div class="wrap">',
        "<header>", f"<h1>{html.escape(brand['account_name'])}</h1>",
        f"<p>{html.escape(brand['tagline'])}</p>", "</header>",
        f'<div class="disclosure">{html.escape(brand["disclosure"])}</div>',
    ]
    if shown == 0:
        parts.append('<p style="text-align:center;color:var(--muted)">清單整理中，很快就來 ✨</p>')
    for niche, items in groups.items():
        parts.append(f"<h2>{html.escape(niche_labels.get(niche, niche))}</h2>")
        for p, link, pending in items:
            sps = [s.strip() for s in p["selling_points"].split("|") if s.strip()]
            parts.append('<div class="card">')
            parts.append('<div class="top">')
            parts.append(f"<h3>{html.escape(p['name'])}</h3>")
            parts.append(f"<span class=\"price\">NT${html.escape(p['price_twd'])}</span>")
            parts.append("</div>")
            if p.get("pain_point"):
                parts.append(f'<div class="tag">{html.escape(p["pain_point"])}</div>')
            parts.append("<ul>" + "".join(f"<li>{html.escape(s)}</li>" for s in sps[:3]) + "</ul>")
            label = "到蝦皮看看 →" if not pending else "查看商品（分潤連結待補）"
            cls = "btn pending" if pending else "btn"
            parts.append(f'<a class="{cls}" href="{html.escape(link)}" target="_blank" rel="noopener nofollow sponsored">{label}</a>')
            parts.append("</div>")
    parts += [
        f"<footer>最後更新 {datetime.now():%Y-%m-%d}</footer>",
        "</div>", "</body>", "</html>",
    ]
    LINKPAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LINKPAGE_PATH.write_text("\n".join(parts), encoding="utf-8")
    return shown


def main():
    parser = argparse.ArgumentParser(description="蝦皮分潤連結整理器")
    parser.add_argument("--include-pending", action="store_true", help="清單頁也放還沒有分潤連結的商品")
    args = parser.parse_args()

    cfg = load_config()
    products = load_products()

    print("=" * 70)
    print(f"蝦皮分潤 — 連結整理器（設定來源：{cfg['_source']}）")
    print("=" * 70)

    status_count = {}
    for p in products:
        _, _, _, status = parse_shopee_url(p["shopee_url"])
        status_count[status] = status_count.get(status, 0) + 1
    print(f"商品數：{len(products)}　網址狀態：{status_count}")

    rows = write_batch(products, cfg)
    print(f"批次表：{BATCH_PATH.relative_to(BASE_DIR)}（{rows} 列 = 商品 × 啟用平台）")

    shown = build_linkpage(products, cfg, include_pending=args.include_pending)
    print(f"清單頁：{LINKPAGE_PATH.relative_to(BASE_DIR)}（放了 {shown} 個商品）")

    filled = sum(1 for p in products if (p.get("affiliate_link") or "").strip())
    if filled == 0:
        print("\n下一步：打開批次表 → 到 affiliate.shopee.tw 後台「商品連結產生器」逐一貼上網址與 sub_id")
        print("        → 把產生的 s.shopee.tw 短連結填回 products.csv 的 affiliate_link 欄 → 再跑一次這支腳本")
    if status_count.get("placeholder"):
        print(f"\n⚠️ 有 {status_count['placeholder']} 個商品還是範例網址（SHOPID/ITEMID），請換成真實商品網址。")


if __name__ == "__main__":
    main()
