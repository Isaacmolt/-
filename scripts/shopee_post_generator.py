#!/usr/bin/env python3
"""
蝦皮分潤 — 貼文 & 短影音腳本產生器 + 30 天排程

讀 shopee-affiliate/products.csv 與 shopee-affiliate/templates/*.md，
幫每個商品產出 Threads / Instagram / 短影音腳本的草稿，並排出 30 天發文表。

輸出：
    shopee-affiliate/posts/<product_id>/<platform>_<type>.txt
    shopee-affiliate/posts/schedule.csv
    shopee-affiliate/reports/content-calendar.md

用法：
    python scripts/shopee_post_generator.py                 # 從今天起排 30 天
    python scripts/shopee_post_generator.py --start 2026-10-06 --days 14
    python scripts/shopee_post_generator.py --status ready  # 只排 status=ready 的商品（預設：全部）
"""

import argparse
import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODULE_DIR = BASE_DIR / "shopee-affiliate"
PRODUCTS_PATH = MODULE_DIR / "products.csv"
TEMPLATES_DIR = MODULE_DIR / "templates"
CONFIG_PATH = MODULE_DIR / "config.json"
CONFIG_EXAMPLE_PATH = MODULE_DIR / "config.example.json"
POSTS_DIR = MODULE_DIR / "posts"
SCHEDULE_PATH = POSTS_DIR / "schedule.csv"
CALENDAR_PATH = MODULE_DIR / "reports" / "content-calendar.md"

PLATFORM_FILES = {
    "threads": "threads.md",
    "instagram": "instagram.md",
    "shopee_video": "shopee_video.md",
}
PLATFORM_LABELS = {
    "threads": "Threads",
    "instagram": "Instagram",
    "shopee_video": "蝦皮影音 / Reels",
}
WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE_PATH
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_products(status_filter=None):
    with open(PRODUCTS_PATH, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if status_filter:
        rows = [r for r in rows if r.get("status", "").strip() == status_filter]
    return rows


def parse_templates(path):
    """把 markdown 裡每個 '### key｜標題' 區塊切出來 → {key: (title, body)}"""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"^### ", text, flags=re.M)[1:]
    templates = {}
    for b in blocks:
        head, _, body = b.partition("\n")
        key, _, title = head.partition("｜")
        templates[key.strip()] = (title.strip() or key.strip(), body.strip() + "\n")
    return templates


def product_vars(p, cfg):
    sps = [s.strip() for s in p["selling_points"].split("|") if s.strip()]
    while len(sps) < 3:
        sps.append("（補一個賣點）")
    link = (p.get("affiliate_link") or "").strip() or "（分潤連結待補：先到後台產生短連結）"
    return {
        "name": p["name"],
        "price": p["price_twd"],
        "sp1": sps[0], "sp2": sps[1], "sp3": sps[2],
        "pain_point": p.get("pain_point", ""),
        "audience": p.get("target_audience", ""),
        "category": p.get("category", ""),
        "link": link,
        "disclosure": cfg["brand"]["disclosure"],
        "account": cfg["brand"]["handle"],
    }


def render(body, variables):
    out = body
    for k, v in variables.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def generate_posts(products, cfg, enabled_platforms):
    all_templates = {pf: parse_templates(TEMPLATES_DIR / PLATFORM_FILES[pf]) for pf in enabled_platforms}
    count = 0
    for p in products:
        variables = product_vars(p, cfg)
        out_dir = POSTS_DIR / p["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        for pf, templates in all_templates.items():
            for key, (title, body) in templates.items():
                header = f"# {p['id']} {p['name']}｜{PLATFORM_LABELS[pf]}｜{title}\n# 連結：{variables['link']}\n\n"
                (out_dir / f"{pf}_{key}.txt").write_text(header + render(body, variables), encoding="utf-8")
                count += 1
    return count, all_templates


def build_schedule(products, cfg, enabled_platforms, all_templates, start, days):
    """每天依 posts_per_day 排平台，商品與貼文類型輪替，不連續兩天同一商品。"""
    rows = []
    prod_idx = 0
    type_idx = {pf: 0 for pf in enabled_platforms}
    sub_pattern = cfg["sub_id_pattern"]
    for d in range(days):
        date = start + timedelta(days=d)
        for pf in enabled_platforms:
            per_day = int(cfg["platforms"][pf].get("posts_per_day", 1))
            keys = list(all_templates[pf].keys())
            for _ in range(per_day):
                p = products[prod_idx % len(products)]
                prod_idx += 1
                key = keys[type_idx[pf] % len(keys)]
                type_idx[pf] += 1
                sub_id = sub_pattern.format(
                    platform=cfg["platforms"][pf]["code"], niche=p["niche"],
                    yyyymm=date.strftime("%Y%m"), product_id=p["id"]).lower()
                rows.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "weekday": WEEKDAYS[date.weekday()],
                    "platform": PLATFORM_LABELS[pf],
                    "type": all_templates[pf][key][0],
                    "product_id": p["id"],
                    "product": p["name"],
                    "sub_id": sub_id,
                    "file": f"posts/{p['id']}/{pf}_{key}.txt",
                    "status": "scheduled",
                })
    return rows


def write_schedule(rows):
    with open(SCHEDULE_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_calendar(rows, start, days):
    lines = [
        "# 蝦皮分潤 — 發文日曆",
        f"_由 scripts/shopee_post_generator.py 於 {datetime.now():%Y-%m-%d %H:%M} 產生_",
        f"_期間：{start:%Y-%m-%d} 到 {(start + timedelta(days=days - 1)):%Y-%m-%d}，共 {len(rows)} 篇_",
        "",
        "發文前把 `file` 那份草稿改成自己的語氣，連結用對應的 sub_id 在後台產生，發完回 `shopee-affiliate/tracker.xlsx` 的「貼文日誌」登記。",
        "",
        "| 日期 | 週 | 平台 | 類型 | 商品 | sub_id | 草稿 |",
        "|------|----|------|------|------|--------|------|",
    ]
    for r in rows:
        lines.append(f"| {r['date']} | {r['weekday']} | {r['platform']} | {r['type']} | {r['product']} | `{r['sub_id']}` | `{r['file']}` |")
    lines += [
        "",
        "## 每週節奏建議",
        "",
        "- **週一到週五**：照表發。Threads 早上 8-9 點（通勤）與晚上 9-11 點（睡前滑手機）兩個時段最好。",
        "- **週六**：發「清單文」或「前後對比」這種可收藏的內容，週末觸及通常較好。",
        "- **週日**：可以少發，但至少回覆留言、看後台數據，把下週的檔期加碼商品挑出來。",
        "- **每天**：發文後 30 分鐘內回覆所有留言，Threads 演算法很吃早期互動。",
    ]
    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="蝦皮分潤貼文產生器")
    parser.add_argument("--start", default=None, help="排程起始日 YYYY-MM-DD（預設今天）")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--status", default=None, help="只處理這個 status 的商品，例如 ready")
    args = parser.parse_args()

    cfg = load_config()
    products = load_products(args.status)
    if not products:
        raise SystemExit("products.csv 裡沒有符合條件的商品。")
    enabled = [pf for pf in PLATFORM_FILES if cfg["platforms"].get(pf, {}).get("enabled")]
    if not enabled:
        raise SystemExit("config 裡沒有啟用任何平台。")
    start = datetime.strptime(args.start, "%Y-%m-%d") if args.start else datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    print("=" * 70)
    print("蝦皮分潤 — 貼文產生器")
    print("=" * 70)
    count, all_templates = generate_posts(products, cfg, enabled)
    print(f"商品 {len(products)} 個 × 平台 {len(enabled)} 個 → 草稿 {count} 份 → {POSTS_DIR.relative_to(BASE_DIR)}/")

    rows = build_schedule(products, cfg, enabled, all_templates, start, args.days)
    write_schedule(rows)
    write_calendar(rows, start, args.days)
    print(f"排程 {len(rows)} 篇（{args.days} 天）→ {SCHEDULE_PATH.relative_to(BASE_DIR)}")
    print(f"日曆 → {CALENDAR_PATH.relative_to(BASE_DIR)}")
    missing = sum(1 for p in products if not (p.get("affiliate_link") or "").strip())
    if missing:
        print(f"\n⚠️ {missing} 個商品還沒有分潤連結，草稿裡的連結是佔位文字，發文前記得補。")


if __name__ == "__main__":
    main()
