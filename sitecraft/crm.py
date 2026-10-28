#!/usr/bin/env python3
"""
SiteCraft — 第 4 步：名單管理（迷你 CRM）
==========================================
所有資料都在 sitecraft/data/leads.csv，用 Excel / Google Sheets 開也可以改。

用法：
    python sitecraft/crm.py stats                        # 漏斗、成交數、預估營收
    python sitecraft/crm.py due                          # 今天該做的事：缺 email 的、該追蹤的、該結案的
    python sitecraft/crm.py list [--status demo_ready] [--city 台中市] [--no-email]
    python sitecraft/crm.py show cafe-7f3a2c
    python sitecraft/crm.py email cafe-7f3a2c owner@shop.tw          # 補 email（Google 地圖沒有 email，要自己找）
    python sitecraft/crm.py contact cafe-7f3a2c --line https://lin.ee/xxx --fb https://facebook.com/xxx --ig https://instagram.com/xxx
    python sitecraft/crm.py note cafe-7f3a2c "老闆說月底再談"
    python sitecraft/crm.py replied cafe-7f3a2c          # 店家回信了
    python sitecraft/crm.py won cafe-7f3a2c              # 收到 860 元
    python sitecraft/crm.py publish cafe-7f3a2c          # 拿掉示範橫幅、正式上線（同一網址）
    python sitecraft/crm.py package cafe-7f3a2c          # 打包 zip 給想自己放主機的店家
    python sitecraft/crm.py lost cafe-7f3a2c / optout cafe-7f3a2c
    python sitecraft/crm.py sweep                        # 最後一封信超過 N 天沒回 → 自動標 lost
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

from common import (
    DELIVERIES_DIR, LEADS_FILE, SITES_DIR, STATUSES, find_lead, load_config, load_env, load_themes,
    parse_day, read_leads, today, write_leads,
)

FUNNEL = ["new", "demo_ready", "contacted", "followup_1", "followup_2", "replied", "won", "delivered"]


def _load() -> tuple[list[dict], dict]:
    load_env()
    return read_leads(LEADS_FILE), load_config()


def _need(rows: list[dict], key: str) -> dict:
    lead = find_lead(rows, key)
    if not lead:
        sys.exit(f"找不到 slug / place_id 為「{key}」的店家。用 crm.py list 看看。")
    return lead


def _table(rows: list[dict], cols: list[tuple[str, int]]) -> None:
    head = "  ".join(f"{c:<{w}}" for c, w in cols)
    print(head)
    print("-" * len(head))
    for r in rows:
        print("  ".join(f"{(r.get(c) or '')[:w]:<{w}}" for c, w in cols))


# ---------------------------------------------------------------------------
def cmd_stats(args, rows, cfg):
    price = int(cfg["brand"].get("price_twd", 860))
    counts = {s: 0 for s in STATUSES}
    for r in rows:
        counts[r.get("status") or "new"] = counts.get(r.get("status") or "new", 0) + 1
    total = len(rows)
    targets = sum(counts[s] for s in FUNNEL)
    emailed = sum(counts[s] for s in ("contacted", "followup_1", "followup_2", "replied", "won", "delivered"))
    won = counts["won"] + counts["delivered"]
    print(f"📊 名單總數 {total}　目標店家 {targets}　已寄信 {emailed}　成交 {won}　營收 NT${won * price:,}")
    print()
    for s in FUNNEL + ["lost", "opted_out", "has_website", "skipped"]:
        bar = "█" * min(counts.get(s, 0), 60)
        print(f"  {s:<12}{counts.get(s, 0):>5}  {bar}")
    if emailed:
        print()
        print(f"  回覆率 {counts['replied'] + won:>4}/{emailed} = {(counts['replied'] + won) / emailed:.0%}"
              f"　成交率 {won}/{emailed} = {won / emailed:.0%}")
    need_email = sum(1 for r in rows if r["status"] == "demo_ready" and not r.get("email"))
    if need_email:
        print(f"\n  ⚠ {need_email} 家示範站做好了但還沒有 email → crm.py due")


def cmd_due(args, rows, cfg):
    out = cfg.get("outreach", {})
    t = date.today()
    need_email = [r for r in rows if r["status"] == "demo_ready" and not r.get("email")]
    ready = [r for r in rows if r["status"] == "demo_ready" and r.get("email")]
    f1 = [r for r in rows if r["status"] == "contacted" and _older(r, out.get("followup1_days", 4))]
    f2 = [r for r in rows if r["status"] == "followup_1" and _older(r, out.get("followup2_days", 5))]
    close = [r for r in rows if r["status"] == "followup_2" and _older(r, out.get("close_after_days", 7))]
    replied = [r for r in rows if r["status"] == "replied"]
    won = [r for r in rows if r["status"] == "won"]

    print(f"📅 {t.isoformat()} 今天的待辦")
    _section("🔍 示範站做好了、還缺 email（去 FB 粉專「關於」、IG 簡介、店家名片找；找不到就改走 LINE / 電話）", need_email,
             "demo_url")
    _section(f"📨 可以寄第一封信（python sitecraft/send_outreach.py --stage first --send）", ready, "email")
    _section("🔁 該寄第一次追蹤信（--stage followup1）", f1, "last_contact_at")
    _section("🔁 該寄最後一封追蹤信（--stage followup2）", f2, "last_contact_at")
    _section("🗂  三封都寄了沒回 → crm.py sweep 結案", close, "last_contact_at")
    _section("💬 有回覆、洽談中（記得回信！）", replied, "notes")
    _section("💰 已付款，等照片文字 → 完成後 crm.py publish <slug>", won, "paid_at")


def _older(r: dict, days) -> bool:
    last = parse_day(r.get("last_contact_at", ""))
    return bool(last) and (date.today() - last).days >= int(days)


def _section(title: str, items: list[dict], extra: str) -> None:
    print()
    print(f"{title}  [{len(items)}]")
    for r in items[:40]:
        print(f"   · {r['slug']:<16} {r['name']:<18} {r.get('city', '')}{r.get('district', '')}  {r.get(extra, '')}")
    if len(items) > 40:
        print(f"   … 還有 {len(items) - 40} 家")


def cmd_list(args, rows, cfg):
    sel = rows
    if args.status:
        sel = [r for r in sel if r["status"] == args.status]
    if args.city:
        sel = [r for r in sel if args.city in (r.get("city") or "")]
    if args.no_email:
        sel = [r for r in sel if not r.get("email")]
    sel.sort(key=lambda r: (r["status"], r.get("city", ""), r.get("district", "")))
    _table(sel, [("slug", 16), ("name", 18), ("status", 11), ("city", 4), ("district", 4),
                 ("category", 8), ("rating", 4), ("review_count", 5), ("email", 26)])
    print(f"\n{len(sel)} 家")


def cmd_show(args, rows, cfg):
    lead = _need(rows, args.slug)
    width = max(len(k) for k in lead)
    for k, v in lead.items():
        if k == "hours_json":
            v = (v[:80] + "…") if len(v) > 80 else v
        print(f"{k:<{width}}  {v}")
    print(f"\n網站檔案：{SITES_DIR / lead['slug'] / 'index.html'}")
    print(f"文案檔案：{SITES_DIR / lead['slug'] / 'content.json'}")


def cmd_set(args, rows, cfg):
    lead = _need(rows, args.slug)
    if args.status not in STATUSES:
        sys.exit(f"狀態必須是：{', '.join(STATUSES)}")
    lead["status"] = args.status
    if args.note:
        lead["notes"] = (lead.get("notes", "") + f" [{today()}] {args.note}").strip()
    write_leads(rows, LEADS_FILE)
    print(f"✓ {lead['name']} → {args.status}")


def cmd_email(args, rows, cfg):
    lead = _need(rows, args.slug)
    if "@" not in args.email:
        sys.exit("這看起來不像 email。")
    lead["email"] = args.email.strip()
    write_leads(rows, LEADS_FILE)
    print(f"✓ {lead['name']} email = {lead['email']}")
    if lead["status"] == "demo_ready":
        print("  可以寄第一封信了：python sitecraft/send_outreach.py --stage first --slug", lead["slug"])


def cmd_contact(args, rows, cfg):
    lead = _need(rows, args.slug)
    for field, val in (("line_url", args.line), ("facebook_url", args.fb), ("instagram_url", args.ig), ("phone", args.phone)):
        if val:
            lead[field] = val.strip()
    write_leads(rows, LEADS_FILE)
    _sync_content(lead)
    print(f"✓ {lead['name']} 聯絡方式已更新（重新 build 後網站會顯示）")


def _sync_content(lead: dict) -> None:
    """把 CSV 裡的聯絡方式同步進 content.json（若存在）。"""
    import json
    cj = SITES_DIR / lead["slug"] / "content.json"
    if not cj.exists():
        return
    try:
        content = json.loads(cj.read_text(encoding="utf-8"))
    except ValueError:
        return
    for k in ("phone", "line_url", "facebook_url", "instagram_url"):
        if lead.get(k):
            content[k] = lead[k]
    cj.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_note(args, rows, cfg):
    lead = _need(rows, args.slug)
    lead["notes"] = (lead.get("notes", "") + f" [{today()}] {args.text}").strip()
    write_leads(rows, LEADS_FILE)
    print(f"✓ 已記錄：{lead['notes']}")


def cmd_replied(args, rows, cfg):
    lead = _need(rows, args.slug)
    lead["status"] = "replied"
    lead["next_action_at"] = today()
    if args.note:
        lead["notes"] = (lead.get("notes", "") + f" [{today()}] {args.note}").strip()
    write_leads(rows, LEADS_FILE)
    print(f"✓ {lead['name']} → replied。記得 24 小時內回覆！")


def cmd_won(args, rows, cfg):
    lead = _need(rows, args.slug)
    lead["status"] = "won"
    lead["paid_at"] = today()
    write_leads(rows, LEADS_FILE)
    price = cfg["brand"].get("price_twd", 860)
    print(f"🎉 {lead['name']} 成交 NT${price}！")
    print(f"   寄資料需求信：python sitecraft/send_outreach.py --stage after_payment --slug {lead['slug']} --send")
    print(f"   收到照片後：把圖放到 {SITES_DIR / lead['slug'] / 'img'}，在 content.json 的 gallery 列出檔名、改文案")
    print(f"   然後：python sitecraft/crm.py publish {lead['slug']}")


def cmd_publish(args, rows, cfg):
    from build_site import build_index, build_one
    lead = _need(rows, args.slug)
    themes = load_themes()
    lead["status"] = "delivered"
    lead["delivered_url"] = lead.get("demo_url") or f"{cfg['brand']['demo_base_url']}/{lead['slug']}/"
    out = build_one(lead, cfg, themes, demo=False)
    build_index(cfg, themes)
    write_leads(rows, LEADS_FILE)
    print(f"✅ {lead['name']} 正式版已產生：{out}")
    print(f"   git add/commit/push 後即上線：{lead['delivered_url']}")
    print(f"   寄上線通知：python sitecraft/send_outreach.py --stage delivered --slug {lead['slug']} --send")


def cmd_package(args, rows, cfg):
    from build_site import build_one
    lead = _need(rows, args.slug)
    themes = load_themes()
    build_one(lead, cfg, themes, demo=False)
    src = SITES_DIR / lead["slug"]
    DELIVERIES_DIR.mkdir(parents=True, exist_ok=True)
    stage = DELIVERIES_DIR / lead["slug"]
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(src, stage, ignore=shutil.ignore_patterns("content.json"))
    (stage / "說明.txt").write_text(
        f"{lead['name']} 官方網站檔案\n\n"
        "1. index.html 就是整個網站，img/ 是照片。\n"
        "2. 上傳到任何靜態主機（Netlify、Cloudflare Pages、GitHub Pages、Vercel）即可，不需要資料庫。\n"
        "3. 想改文字可以用記事本打開 index.html 直接改，或聯絡我們免費小改。\n"
        f"\n網站製作：{cfg['brand']['sender_name']}\n", encoding="utf-8")
    zip_path = shutil.make_archive(str(DELIVERIES_DIR / f"{lead['slug']}-website"), "zip", stage)
    shutil.rmtree(stage)
    print(f"📦 已打包：{zip_path}")


def cmd_lost(args, rows, cfg):
    lead = _need(rows, args.slug)
    lead["status"] = "lost"
    if args.note:
        lead["notes"] = (lead.get("notes", "") + f" [{today()}] {args.note}").strip()
    write_leads(rows, LEADS_FILE)
    print(f"✓ {lead['name']} → lost（示範站可保留，日後想再談隨時 crm.py set <slug> replied）")


def cmd_optout(args, rows, cfg):
    lead = _need(rows, args.slug)
    lead["status"] = "opted_out"
    lead["notes"] = (lead.get("notes", "") + f" [{today()} 要求停止聯絡]").strip()
    write_leads(rows, LEADS_FILE)
    print(f"✓ {lead['name']} → opted_out，永不再寄")


def cmd_sweep(args, rows, cfg):
    days = int(cfg.get("outreach", {}).get("close_after_days", 7))
    n = 0
    for r in rows:
        if r["status"] == "followup_2" and _older(r, days):
            r["status"] = "lost"
            r["notes"] = (r.get("notes", "") + f" [{today()} 三封未回自動結案]").strip()
            n += 1
    write_leads(rows, LEADS_FILE)
    print(f"✓ 結案 {n} 家（最後一封超過 {days} 天未回）")


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="SiteCraft 迷你 CRM")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    sub.add_parser("due")
    p = sub.add_parser("list"); p.add_argument("--status"); p.add_argument("--city"); p.add_argument("--no-email", action="store_true")
    p = sub.add_parser("show"); p.add_argument("slug")
    p = sub.add_parser("set"); p.add_argument("slug"); p.add_argument("status"); p.add_argument("--note")
    p = sub.add_parser("email"); p.add_argument("slug"); p.add_argument("email")
    p = sub.add_parser("contact"); p.add_argument("slug"); p.add_argument("--line"); p.add_argument("--fb"); p.add_argument("--ig"); p.add_argument("--phone")
    p = sub.add_parser("note"); p.add_argument("slug"); p.add_argument("text")
    p = sub.add_parser("replied"); p.add_argument("slug"); p.add_argument("--note")
    p = sub.add_parser("won"); p.add_argument("slug")
    p = sub.add_parser("publish"); p.add_argument("slug")
    p = sub.add_parser("package"); p.add_argument("slug")
    p = sub.add_parser("lost"); p.add_argument("slug"); p.add_argument("--note")
    p = sub.add_parser("optout"); p.add_argument("slug")
    sub.add_parser("sweep")
    args = ap.parse_args()

    rows, cfg = _load()
    if not rows and args.cmd not in ("stats",):
        sys.exit("名單是空的。先跑 python sitecraft/find_leads.py --city 台中市 --type 咖啡廳")
    globals()[f"cmd_{args.cmd}"](args, rows, cfg)


if __name__ == "__main__":
    main()
