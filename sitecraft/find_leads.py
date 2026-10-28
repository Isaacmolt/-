#!/usr/bin/env python3
"""
SiteCraft — 第 1 步：從 Google 地圖找「還沒有官網」的商家
==========================================================
使用官方 Google Places API (New) 的 Text Search，不爬網頁、不違反條款。

用法：
    python sitecraft/find_leads.py --city 台中市 --district 西區 --type 咖啡廳
    python sitecraft/find_leads.py --city 台中市 --type 咖啡廳 --type 美髮沙龍     # 掃該市所有行政區
    python sitecraft/find_leads.py --city 台中市                                     # 用 config.json 裡全部類型（很多請求，注意額度）
    python sitecraft/find_leads.py --query "台中 西區 寵物美容" --pages 2
    python sitecraft/find_leads.py --city 台中市 --type 咖啡廳 --dry-run            # 只列出會查哪些關鍵字

環境變數（.env）：
    GOOGLE_MAPS_API_KEY  — 需在 Google Cloud 啟用 "Places API (New)"

費用提醒：
    我們要讀 websiteUri / 電話 / 營業時間 / 評分，屬於 Text Search「Enterprise」SKU，
    每個月約有 1,000 次免費請求（之後約 US$35 / 1,000 次，請以 Google 定價頁為準）。
    一次請求最多回 20 家、一組關鍵字最多翻 3 頁（60 家）。
    例：10 個行政區 × 10 種類型 × 3 頁 = 300 次請求 ≈ 6,000 家店，仍在免費額度內。
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import requests

from common import (
    LEADS_FILE, LEAD_FIELDS, env, load_config, load_env, load_themes, make_slug,
    parse_tw_address, pick_theme, read_leads, today, website_status, write_leads, demo_url_for,
)

API_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.nationalPhoneNumber", "places.websiteUri",
    "places.rating", "places.userRatingCount",
    "places.primaryTypeDisplayName", "places.primaryType",
    "places.regularOpeningHours", "places.googleMapsUri", "places.businessStatus",
    "nextPageToken",
])
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def search_text(api_key: str, query: str, language: str, region: str, pages: int) -> list[dict]:
    """跑一組關鍵字、翻 pages 頁，回傳 place dict 列表。"""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    results: list[dict] = []
    page_token = None
    for page in range(pages):
        body = {"textQuery": query, "languageCode": language, "regionCode": region, "pageSize": 20}
        if page_token:
            body["pageToken"] = page_token
        data = _post_with_retry(headers, body)
        if data is None:
            break
        places = data.get("places", [])
        results.extend(places)
        page_token = data.get("nextPageToken")
        if not page_token or len(places) < 20:
            break
    return results


def _post_with_retry(headers: dict, body: dict) -> dict | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, headers=headers, json=body, timeout=30)
        except requests.RequestException as exc:
            print(f"    ! 連線錯誤（第 {attempt} 次）：{exc}")
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 500, 502, 503, 504):
            print(f"    ! HTTP {resp.status_code}，{2 ** attempt}s 後重試")
            time.sleep(2 ** attempt)
            continue
        # 400/403：金鑰、API 未啟用、欄位錯誤——直接說清楚，不重試
        try:
            msg = resp.json().get("error", {}).get("message", resp.text)
        except ValueError:
            msg = resp.text
        print(f"    x HTTP {resp.status_code}：{msg}")
        if resp.status_code == 403:
            print("      → 請到 Google Cloud Console 確認已啟用「Places API (New)」且金鑰沒有限制來源。")
        return None
    return None


# ---------------------------------------------------------------------------
# 轉成名單
# ---------------------------------------------------------------------------
def place_to_lead(place: dict, query: str, cfg: dict, themes: dict) -> dict:
    name = (place.get("displayName") or {}).get("text", "").strip()
    address = place.get("formattedAddress", "")
    city, district = parse_tw_address(address)
    category = (place.get("primaryTypeDisplayName") or {}).get("text", "") or place.get("primaryType", "")
    uri = place.get("websiteUri", "")
    status = website_status(uri, cfg["search"]["social_domains"])
    theme_key, _ = pick_theme(themes, category, name, query)
    hours = place.get("regularOpeningHours") or {}
    hours_json = json.dumps({
        "weekday": hours.get("weekdayDescriptions", []),
        "periods": hours.get("periods", []),
    }, ensure_ascii=False) if hours else ""
    place_id = place.get("id", "")
    slug = make_slug(theme_key, place_id)

    biz_status = place.get("businessStatus", "OPERATIONAL")
    review_count = int(place.get("userRatingCount") or 0)
    min_reviews = int(cfg["search"].get("min_reviews", 0))
    social_ok = cfg["search"].get("treat_social_as_no_website", True)

    if biz_status != "OPERATIONAL":
        lead_status = "skipped"
    elif status == "real":
        lead_status = "has_website"
    elif status == "social" and not social_ok:
        lead_status = "has_website"
    elif review_count < min_reviews:
        lead_status = "skipped"
    else:
        lead_status = "new"

    return {
        "place_id": place_id,
        "name": name,
        "slug": slug,
        "query": query,
        "category": category,
        "theme": theme_key,
        "address": address,
        "city": city,
        "district": district,
        "phone": place.get("nationalPhoneNumber", ""),
        "website_uri": uri,
        "website_status": status,
        "rating": str(place.get("rating", "") or ""),
        "review_count": str(review_count),
        "maps_url": place.get("googleMapsUri", ""),
        "hours_json": hours_json,
        "business_status": biz_status,
        "demo_url": demo_url_for(slug, cfg) if lead_status == "new" else "",
        "status": lead_status,
        "first_seen": today(),
        "followup_count": "0",
    }


# 既有名單裡要保留、不被重新抓取覆蓋的欄位
KEEP_ON_MERGE = {
    "slug", "email", "line_url", "facebook_url", "instagram_url", "demo_url", "status",
    "first_seen", "first_contact_at", "last_contact_at", "followup_count",
    "next_action_at", "paid_at", "delivered_url", "notes", "theme",
}


def merge_leads(existing: list[dict], fresh: list[dict]) -> tuple[list[dict], int, int]:
    by_id = {r["place_id"]: r for r in existing if r.get("place_id")}
    added = updated = 0
    for lead in fresh:
        pid = lead["place_id"]
        if pid in by_id:
            cur = by_id[pid]
            for k, v in lead.items():
                if k in KEEP_ON_MERGE:
                    continue
                cur[k] = v
            # 之前是目標、現在突然有官網了 → 除非已成交，否則標記 has_website
            if lead["website_status"] == "real" and cur["status"] not in ("won", "delivered", "replied"):
                cur["status"] = "has_website"
            updated += 1
        else:
            row = {k: "" for k in LEAD_FIELDS}
            row.update(lead)
            by_id[pid] = row
            added += 1
    return list(by_id.values()), added, updated


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_queries(args: argparse.Namespace, cfg: dict) -> list[str]:
    if args.query:
        return list(args.query)
    if not args.city:
        sys.exit("請指定 --city（例如 --city 台中市）或 --query。")
    districts = list(args.district) if args.district else cfg["cities"].get(args.city, [""])
    types = list(args.type) if args.type else cfg["types"]
    queries = []
    for d in districts:
        for t in types:
            queries.append(f"{args.city}{d} {t}".strip())
    return queries


def main() -> None:
    ap = argparse.ArgumentParser(description="從 Google 地圖找沒有官網的商家")
    ap.add_argument("--city", help="縣市，例如 台中市")
    ap.add_argument("--district", action="append", help="行政區，可重複；不給就掃 config 裡該市全部")
    ap.add_argument("--type", action="append", help="店家類型，可重複；不給就用 config 裡全部類型")
    ap.add_argument("--query", action="append", help="直接給完整關鍵字，可重複（會忽略 --city/--type）")
    ap.add_argument("--pages", type=int, default=None, help="每組關鍵字翻幾頁（每頁 20 家，最多 3）")
    ap.add_argument("--out", default=str(LEADS_FILE), help="輸出 CSV（預設 sitecraft/data/leads.csv）")
    ap.add_argument("--dry-run", action="store_true", help="只列出會查的關鍵字與預估請求數，不呼叫 API")
    args = ap.parse_args()

    load_env()
    cfg = load_config()
    themes = load_themes()
    pages = min(max(args.pages or cfg["search"].get("pages_per_query", 3), 1), 3)
    queries = build_queries(args, cfg)

    print(f"[search] 共 {len(queries)} 組關鍵字 × 最多 {pages} 頁 = 最多 {len(queries) * pages} 次 API 請求")
    if args.dry_run:
        for q in queries:
            print("   ·", q)
        return

    api_key = env("GOOGLE_MAPS_API_KEY")
    if not api_key:
        sys.exit("缺少 GOOGLE_MAPS_API_KEY，請複製 .env.example 成 .env 並填入金鑰。")

    from pathlib import Path
    out_path = Path(args.out)
    existing = read_leads(out_path)
    fresh: list[dict] = []
    seen: set[str] = set()
    lang, region = cfg["search"]["language"], cfg["search"]["region"]

    for i, q in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {q}")
        places = search_text(api_key, q, lang, region, pages)
        n_new = 0
        for p in places:
            if not p.get("id") or p["id"] in seen:
                continue
            seen.add(p["id"])
            fresh.append(place_to_lead(p, q, cfg, themes))
            n_new += 1
        print(f"    取得 {len(places)} 家（新 {n_new}）")
        time.sleep(0.3)

    merged, added, updated = merge_leads(existing, fresh)
    write_leads(merged, out_path)

    targets = [r for r in fresh if r["status"] == "new"]
    social = [r for r in targets if r["website_status"] == "social"]
    print()
    print("=" * 60)
    print(f"[ok] 寫入 {out_path}（新增 {added}、更新 {updated}）")
    print(f"   本次掃到 {len(fresh)} 家 → 沒有官網的目標 {len(targets)} 家"
          f"（其中只有 FB/IG/LINE 的 {len(social)} 家）")
    print(f"   已有官網 {sum(1 for r in fresh if r['status'] == 'has_website')} 家、"
          f"略過 {sum(1 for r in fresh if r['status'] == 'skipped')} 家")
    print()
    print("下一步：python sitecraft/build_site.py            # 幫所有 new 的店家產生示範網站")
    print("        python sitecraft/crm.py list --status new  # 看名單、補 email")


if __name__ == "__main__":
    main()
