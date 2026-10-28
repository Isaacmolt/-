#!/usr/bin/env python3
"""
SiteCraft — 第 3 步：寄信給店家（合併列印 + 追蹤）
===================================================
預設是「預覽模式」：不會真的寄，只把每封信存到 sitecraft/outbox/ 讓你檢查。
加 --send 才會透過 SMTP 真的寄出，並更新名單狀態與 sent_log.csv。

用法：
    python sitecraft/send_outreach.py --stage first                  # 預覽：所有 demo_ready 且有 email 的店家
    python sitecraft/send_outreach.py --stage first --send --limit 20
    python sitecraft/send_outreach.py --stage followup1 --send        # 第一封後 4 天未回覆
    python sitecraft/send_outreach.py --stage followup2 --send        # 再 5 天未回覆（最後一封）
    python sitecraft/send_outreach.py --stage after_payment --slug cafe-7f3a2c --send
    python sitecraft/send_outreach.py --stage delivered --slug cafe-7f3a2c --send
    python sitecraft/send_outreach.py --test you@example.com          # 寄一封測試信給自己，確認 SMTP 設定
    python sitecraft/send_outreach.py --opt-out owner@shop.tw         # 店家說不要再寄 → 永久停止

環境變數（.env）：
    SMTP_HOST=smtp.gmail.com  SMTP_PORT=587  SMTP_USER=you@gmail.com  SMTP_PASS=<Gmail 應用程式密碼>
    SENDER_NAME=SiteCraft 小站工作室  SENDER_EMAIL=you@gmail.com  REPLY_TO=you@gmail.com
    SENDER_PERSON=你的名字  CONTACT_LINE=@your-line-id  CONTACT_PHONE=09xx-xxx-xxx

寄信禮儀（寫進程式的保護）：
    - 每天上限（config.outreach.daily_cap，預設 30）；Gmail 個人帳號理論上限 500/天，但冷信寄太多會被判垃圾信
    - 每封之間隨機間隔 60～150 秒
    - 每封信底部都有「回覆不用了即可停止」；標記 opted_out 的永不再寄
    - 同一家店最多 3 封（first → followup1 → followup2），之後自動結案
"""

from __future__ import annotations

import argparse
import html
import random
import re
import smtplib
import sys
import time
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

from jinja2 import Environment, BaseLoader

from common import (
    LEADS_FILE, NEVER_EMAIL, OUTBOX_DIR, SENT_LOG_FILE, TEMPLATES_DIR, append_sent_log, days_from_today,
    env, find_lead, fmt_rating, load_config, load_env, now, parse_day, read_leads, today, write_leads,
)
import csv
from datetime import date

STAGES = {
    # stage: (template, 寄前狀態, 寄後狀態, 下次動作天數)
    "first":         ("01_first_touch.txt",   {"demo_ready"},  "contacted",  "followup1_days"),
    "followup1":     ("02_followup.txt",      {"contacted"},   "followup_1", "followup2_days"),
    "followup2":     ("03_last_call.txt",     {"followup_1"},  "followup_2", "close_after_days"),
    "after_payment": ("04_after_payment.txt", {"won"},         None,         None),
    "delivered":     ("05_delivered.txt",     {"delivered"},   None,         None),
}

_jinja = Environment(loader=BaseLoader(), autoescape=False, trim_blocks=True, lstrip_blocks=True)


# ---------------------------------------------------------------------------
# 範本
# ---------------------------------------------------------------------------
def render_template(template_name: str, ctx: dict) -> tuple[str, str]:
    raw = (TEMPLATES_DIR / "email" / template_name).read_text(encoding="utf-8")
    rendered = _jinja.from_string(raw).render(**ctx).strip()
    first, _, body = rendered.partition("\n")
    subject = first.replace("Subject:", "", 1).strip()
    return subject, body.strip() + "\n"


URL_RE = re.compile(r"(https?://[^\s<>\"]+)")


def text_to_html(body: str) -> str:
    paragraphs = []
    for block in re.split(r"\n\s*\n", body.strip()):
        esc = html.escape(block)
        esc = URL_RE.sub(r'<a href="\1" style="color:#1d4ed8;font-weight:600">\1</a>', esc)
        esc = esc.replace("\n", "<br>")
        paragraphs.append(f'<p style="margin:0 0 14px">{esc}</p>')
    return (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Noto Sans TC\',\'PingFang TC\','
        '\'Microsoft JhengHei\',sans-serif;font-size:15px;line-height:1.75;color:#1f2937;max-width:620px">'
        + "".join(paragraphs) + "</div>"
    )


def build_context(lead: dict, cfg: dict) -> dict:
    brand = cfg["brand"]
    return {
        **lead,
        "rating": fmt_rating(lead.get("rating", "")),
        "sender_name": brand["sender_name"],
        "sender_person": brand.get("sender_person", ""),
        "contact_line": brand.get("contact_line", ""),
        "contact_phone": brand.get("contact_phone", ""),
        "price_twd": brand.get("price_twd", 860),
        "hosting_years_included": brand.get("hosting_years_included", 1),
        "turnaround_days": brand.get("turnaround_days", 3),
    }


# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------
class Mailer:
    def __init__(self, cfg: dict) -> None:
        self.host = env("SMTP_HOST", "smtp.gmail.com")
        self.port = int(env("SMTP_PORT", "587"))
        self.user = env("SMTP_USER")
        self.password = env("SMTP_PASS")
        self.sender_email = env("SENDER_EMAIL", self.user)
        self.sender_name = cfg["brand"]["sender_name"]
        self.reply_to = env("REPLY_TO", self.sender_email)
        self._conn: smtplib.SMTP | None = None

    def check(self) -> None:
        missing = [k for k, v in (("SMTP_USER", self.user), ("SMTP_PASS", self.password)) if not v]
        if missing:
            sys.exit(f"缺少 {', '.join(missing)}。請在 .env 設定（Gmail 要用「應用程式密碼」，不是登入密碼）。")

    def connect(self) -> None:
        if self._conn:
            return
        conn = smtplib.SMTP(self.host, self.port, timeout=30)
        conn.ehlo()
        conn.starttls()
        conn.ehlo()
        conn.login(self.user, self.password)
        self._conn = conn

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.quit()
            except smtplib.SMTPException:
                pass
            self._conn = None

    def compose(self, to_email: str, to_name: str, subject: str, body: str) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = formataddr((self.sender_name, self.sender_email))
        msg["To"] = formataddr((to_name, to_email)) if to_name else to_email
        msg["Subject"] = subject
        msg["Reply-To"] = self.reply_to
        msg["Message-ID"] = make_msgid(domain=self.sender_email.partition("@")[2] or None)
        msg.set_content(body)
        msg.add_alternative(text_to_html(body), subtype="html")
        return msg

    def send(self, msg: EmailMessage) -> None:
        self.connect()
        assert self._conn
        self._conn.send_message(msg)


# ---------------------------------------------------------------------------
# 選取對象
# ---------------------------------------------------------------------------
def sent_today_count() -> int:
    if not SENT_LOG_FILE.exists():
        return 0
    t = today()
    with SENT_LOG_FILE.open(newline="", encoding="utf-8") as f:
        return sum(1 for r in csv.DictReader(f) if r.get("sent_at", "").startswith(t) and r.get("mode") == "sent")


def pick_targets(rows: list[dict], stage: str, cfg: dict, slugs: list[str] | None) -> list[dict]:
    template, before, _after, _days = STAGES[stage]
    out = cfg.get("outreach", {})
    picked = []
    for r in rows:
        if slugs and r["slug"] not in slugs:
            continue
        if r["status"] in NEVER_EMAIL and stage != "delivered":
            continue
        if r["status"] not in before:
            continue
        if not r.get("email"):
            continue
        # 追蹤信要等夠久
        if stage == "followup1":
            last = parse_day(r.get("last_contact_at", ""))
            if not last or (date.today() - last).days < int(out.get("followup1_days", 4)):
                continue
        if stage == "followup2":
            last = parse_day(r.get("last_contact_at", ""))
            if not last or (date.today() - last).days < int(out.get("followup2_days", 5)):
                continue
        picked.append(r)
    return picked


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="寄信給名單裡的店家（預設只預覽）")
    ap.add_argument("--stage", choices=list(STAGES), help="寄哪一階段的信")
    ap.add_argument("--slug", action="append", help="只寄給指定 slug（可重複）")
    ap.add_argument("--limit", type=int, default=None, help="本次最多寄幾封")
    ap.add_argument("--send", action="store_true", help="真的寄出（否則只存到 outbox/ 預覽）")
    ap.add_argument("--no-wait", action="store_true", help="封與封之間不等待（測試用，不建議）")
    ap.add_argument("--test", metavar="EMAIL", help="寄一封第一階段的測試信到這個信箱")
    ap.add_argument("--opt-out", metavar="EMAIL", help="把這個 email 的店家標記為 opted_out")
    args = ap.parse_args()

    load_env()
    cfg = load_config()
    out_cfg = cfg.get("outreach", {})
    rows = read_leads(LEADS_FILE)

    if args.opt_out:
        hits = [r for r in rows if r.get("email", "").lower() == args.opt_out.lower()]
        if not hits:
            sys.exit(f"名單裡沒有 email 為 {args.opt_out} 的店家。")
        for r in hits:
            r["status"] = "opted_out"
            r["notes"] = (r.get("notes", "") + f" [{today()} 要求停止聯絡]").strip()
        write_leads(rows, LEADS_FILE)
        print(f"✅ 已將 {len(hits)} 家店標記為 opted_out，永不再寄：{', '.join(r['name'] for r in hits)}")
        return

    mailer = Mailer(cfg)
    if not mailer.sender_email:
        print("⚠ 尚未設定 SMTP_USER / SENDER_EMAIL（.env），預覽信的寄件人會是空的；真的寄送前請先設定。")

    if args.test:
        mailer.check()
        sample = rows[0] if rows else {
            "name": "範例咖啡", "slug": "demo-cafe", "district": "西區", "city": "台中市", "category": "咖啡廳",
            "rating": "4.7", "review_count": "128", "demo_url": cfg["brand"]["demo_base_url"] + "/demo-cafe/",
            "line_url": "", "email": args.test,
        }
        subject, body = render_template("01_first_touch.txt", build_context(sample, cfg))
        msg = mailer.compose(args.test, "", f"[測試] {subject}", body)
        mailer.send(msg)
        mailer.close()
        print(f"✅ 測試信已寄到 {args.test}，去收信看看格式。")
        return

    if not args.stage:
        ap.error("請指定 --stage（first / followup1 / followup2 / after_payment / delivered）")

    template, _before, after, days_key = STAGES[args.stage]
    targets = pick_targets(rows, args.stage, cfg, args.slug)
    if not targets:
        print("沒有符合條件的店家。")
        print("  · first 需要 status=demo_ready 且有 email → 用 crm.py email <slug> <email> 補")
        print("  · followup 需要等夠天數（config.outreach）")
        return

    cap = int(out_cfg.get("daily_cap", 30))
    already = sent_today_count()
    remaining = max(cap - already, 0)
    if args.send and remaining == 0:
        sys.exit(f"今天已寄 {already} 封，達到每日上限 {cap}。明天再寄，或調整 config.outreach.daily_cap。")
    limit = min(args.limit or len(targets), remaining if args.send else len(targets))
    targets = targets[:limit]

    mode = "sent" if args.send else "preview"
    if args.send:
        mailer.check()
    else:
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'📨 寄出' if args.send else '👀 預覽'} {len(targets)} 封「{args.stage}」信"
          f"{f'（今日已寄 {already}/{cap}）' if args.send else ''}")
    print("-" * 60)

    lo, hi = int(out_cfg.get("min_interval_seconds", 60)), int(out_cfg.get("max_interval_seconds", 150))
    sent = 0
    for i, lead in enumerate(targets, 1):
        subject, body = render_template(template, build_context(lead, cfg))
        msg = mailer.compose(lead["email"], lead["name"], subject, body)
        if args.send:
            try:
                mailer.send(msg)
            except smtplib.SMTPAuthenticationError:
                mailer.close()
                sys.exit("SMTP 登入失敗：Gmail 請確認已開兩步驟驗證並使用 16 碼「應用程式密碼」。")
            except smtplib.SMTPException as exc:
                print(f"  ✗ {lead['name']} 寄送失敗：{exc}")
                continue
            stamp = now()
            if after:
                lead["status"] = after
                if args.stage == "first":
                    lead["first_contact_at"] = stamp
                if args.stage.startswith("followup"):
                    lead["followup_count"] = str(int(lead.get("followup_count") or 0) + 1)
                lead["next_action_at"] = days_from_today(int(out_cfg.get(days_key, 4))) if days_key else ""
            lead["last_contact_at"] = stamp
            print(f"  ✓ [{i}/{len(targets)}] {lead['name']} <{lead['email']}>  {subject}")
        else:
            path = OUTBOX_DIR / f"{lead['slug']}-{args.stage}.eml"
            path.write_bytes(bytes(msg))
            print(f"  · [{i}/{len(targets)}] {lead['name']} <{lead['email']}>")
            print(f"      主旨：{subject}")
            print(f"      預覽：{path.relative_to(OUTBOX_DIR.parent.parent)}")
        append_sent_log({"sent_at": now(), "stage": args.stage, "slug": lead["slug"], "name": lead["name"],
                         "email": lead["email"], "subject": subject, "mode": mode})
        sent += 1
        if args.send and i < len(targets) and not args.no_wait:
            wait = random.randint(lo, hi)
            print(f"      ⏳ 等 {wait}s…")
            time.sleep(wait)

    mailer.close()
    if args.send:
        write_leads(rows, LEADS_FILE)
        print("-" * 60)
        print(f"✅ 已寄 {sent} 封並更新名單。有人回信 → python sitecraft/crm.py replied <slug>")
    else:
        print("-" * 60)
        print(f"預覽 {sent} 封已存到 sitecraft/outbox/。確認沒問題後加 --send 真的寄出。")


if __name__ == "__main__":
    main()
