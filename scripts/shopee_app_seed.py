#!/usr/bin/env python3
"""
蝦皮分潤 — 應用程式資料種子（data.json）

把 products.csv、config、posts/schedule.csv 與草稿文字整理成
shopee-affiliate/app/data.json，給網頁應用（手機/電腦）與 Threads 自動發文機器人共用。

- 第一次：python scripts/shopee_app_seed.py
- 已有 data.json 時預設不覆蓋（裡面有你在 App 填的數據）；要重建加 --force，
  會保留既有的 daily 數據與已發佈/錯誤的排程項目，只重建商品與未發佈排程。

data.json 不會包含任何 token，可以安心 commit。
"""

import argparse
import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODULE_DIR = BASE_DIR / "shopee-affiliate"
PRODUCTS_PATH = MODULE_DIR / "products.csv"
CONFIG_PATH = MODULE_DIR / "config.json"
CONFIG_EXAMPLE_PATH = MODULE_DIR / "config.example.json"
SCHEDULE_PATH = MODULE_DIR / "posts" / "schedule.csv"
DATA_PATH = MODULE_DIR / "app" / "data.json"

TZ = timezone(timedelta(hours=8))  # Asia/Taipei
PLATFORM_CODE = {"Threads": "threads", "Instagram": "instagram", "蝦皮影音 / Reels": "shopee_video"}
SLOTS = {"threads": ["09:00", "21:00"], "instagram": ["20:00"], "shopee_video": ["19:00"]}
TYPE_LABELS = {
    "pain_point": "痛點共鳴", "before_after": "前後對比", "one_liner": "一句話推薦",
    "listicle": "清單文", "campaign": "檔期提醒", "carousel": "輪播圖文", "reels": "Reels 文案",
    "demo_15s": "15 秒實測", "compare_30s": "30 秒對比",
}


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE_PATH
    return json.load(open(path, encoding="utf-8"))


def load_products():
    with open(PRODUCTS_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for p in rows:
        out.append({
            "id": p["id"], "niche": p["niche"], "category": p["category"], "name": p["name"],
            "price": float(p["price_twd"] or 0), "pct": float(p["est_commission_pct"] or 0),
            "selling_points": [s.strip() for s in p["selling_points"].split("|") if s.strip()],
            "pain_point": p.get("pain_point", ""), "audience": p.get("target_audience", ""),
            "shopee_url": p.get("shopee_url", ""), "affiliate_link": p.get("affiliate_link", ""),
            "status": p.get("status", "idea") or "idea", "notes": p.get("notes", ""),
        })
    return out


def read_post_text(rel_file):
    path = MODULE_DIR / rel_file
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    body = [l for l in lines if not l.startswith("# ")]
    return "\n".join(body).strip()


def load_schedule(products_by_id):
    if not SCHEDULE_PATH.exists():
        return []
    with open(SCHEDULE_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    items = []
    slot_counter = {}
    for r in rows:
        platform = PLATFORM_CODE.get(r["platform"], "threads")
        key = (r["date"], platform)
        n = slot_counter.get(key, 0)
        slot_counter[key] = n + 1
        slots = SLOTS[platform]
        hhmm = slots[min(n, len(slots) - 1)]
        dt = datetime.strptime(f"{r['date']} {hhmm}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        type_key = Path(r["file"]).stem.split("_", 1)[1]
        product = products_by_id.get(r["product_id"], {})
        items.append({
            "id": f"{r['date']}-{platform}-{n}-{r['product_id']}".lower(),
            "datetime": dt.isoformat(),
            "platform": platform,
            "product_id": r["product_id"],
            "type": type_key,
            "type_label": TYPE_LABELS.get(type_key, r["type"]),
            "sub_id": r["sub_id"],
            "text": read_post_text(r["file"]),
            "link": product.get("affiliate_link", ""),
            "status": "scheduled",
            "auto": platform == "threads",
            "posted_id": "", "posted_at": "", "error": "",
        })
    return items


def build(cfg, existing=None):
    products = load_products()
    by_id = {p["id"]: p for p in products}
    schedule = load_schedule(by_id)
    data = {
        "version": 1,
        "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "brand": cfg["brand"],
        "settings": {
            "timezone": "Asia/Taipei",
            "link_mode": "reply",
            "autopost": {"threads": False},
            "goals": {k: v for k, v in cfg.get("goals", {}).items()},
            "slots": SLOTS,
            "sub_id_pattern": cfg.get("sub_id_pattern", "{platform}_{niche}_{yyyymm}_{product_id}"),
            "github": {"owner": "", "repo": "", "branch": "", "path": "shopee-affiliate/app/data.json"},
        },
        "products": products,
        "schedule": schedule,
        "daily": [],
    }
    if existing:
        data["daily"] = existing.get("daily", [])
        data["settings"]["autopost"] = existing.get("settings", {}).get("autopost", data["settings"]["autopost"])
        data["settings"]["github"] = existing.get("settings", {}).get("github", data["settings"]["github"])
        data["settings"]["link_mode"] = existing.get("settings", {}).get("link_mode", "reply")
        keep = [s for s in existing.get("schedule", []) if s.get("status") in ("posted", "error", "skipped")]
        keep_ids = {s["id"] for s in keep}
        data["schedule"] = keep + [s for s in schedule if s["id"] not in keep_ids]
    data["schedule"].sort(key=lambda s: s["datetime"])
    return data


def main():
    parser = argparse.ArgumentParser(description="蝦皮分潤 App 資料種子")
    parser.add_argument("--force", action="store_true", help="已有 data.json 也重建（保留 daily 與已發佈項目）")
    args = parser.parse_args()
    cfg = load_config()
    existing = None
    if DATA_PATH.exists():
        if not args.force:
            print(f"{DATA_PATH.relative_to(BASE_DIR)} 已存在，未覆蓋。要重建請加 --force。")
            return
        existing = json.load(open(DATA_PATH, encoding="utf-8"))
    data = build(cfg, existing)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=" * 70)
    print("蝦皮分潤 — App 資料種子")
    print("=" * 70)
    print(f"已寫入：{DATA_PATH.relative_to(BASE_DIR)}")
    print(f"商品 {len(data['products'])} 個｜排程 {len(data['schedule'])} 篇｜每日數據 {len(data['daily'])} 筆")
    print("提醒：settings.autopost.threads 預設關閉，在 App 設定裡打開後，機器人才會真的發文。")


if __name__ == "__main__":
    main()
