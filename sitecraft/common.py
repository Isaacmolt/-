#!/usr/bin/env python3
"""
SiteCraft — 共用工具
====================
給 find_leads.py / build_site.py / send_outreach.py / crm.py 共用的
路徑、設定、CSV 讀寫、主題配對、台灣地址/電話解析等小工具。
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# 路徑
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent            # sitecraft/
PROJECT_ROOT = ROOT.parent
DATA_DIR = ROOT / "data"
SITES_DIR = ROOT / "sites"
TEMPLATES_DIR = ROOT / "templates"
OUTBOX_DIR = ROOT / "outbox"
DELIVERIES_DIR = ROOT / "deliveries"

CONFIG_FILE = ROOT / "config.json"
THEMES_FILE = DATA_DIR / "themes.json"
LEADS_FILE = DATA_DIR / "leads.csv"
SAMPLE_LEADS_FILE = DATA_DIR / "leads.sample.csv"
SENT_LOG_FILE = DATA_DIR / "sent_log.csv"

# ---------------------------------------------------------------------------
# 名單欄位與狀態
# ---------------------------------------------------------------------------
LEAD_FIELDS = [
    "place_id", "name", "slug", "query", "category", "theme",
    "address", "city", "district", "phone",
    "website_uri", "website_status",          # website_status: none | social | real
    "rating", "review_count", "maps_url", "hours_json", "business_status",
    "email", "line_url", "facebook_url", "instagram_url",
    "demo_url", "status",
    "first_seen", "first_contact_at", "last_contact_at", "followup_count",
    "next_action_at", "paid_at", "delivered_url", "notes",
]

STATUSES = {
    "new":         "剛從 Google 地圖找到，還沒做網站",
    "demo_ready":  "示範網站已產生，等待寄信",
    "contacted":   "已寄第一封信",
    "followup_1":  "已寄第一次追蹤信",
    "followup_2":  "已寄最後一封追蹤信",
    "replied":     "店家有回覆，洽談中",
    "won":         "已付款，等待照片/文字後上線",
    "delivered":   "已正式上線交付",
    "lost":        "店家婉拒或無回應，結案",
    "opted_out":   "店家要求不要再聯絡（永不再寄）",
    "has_website": "已經有真正的官網，不是目標",
    "skipped":     "歇業/評論太少等原因略過",
}

# 可以寄信的狀態（排除永不再寄）
NEVER_EMAIL = {"opted_out", "has_website", "skipped", "lost", "delivered"}

SENT_LOG_FIELDS = ["sent_at", "stage", "slug", "name", "email", "subject", "mode"]


# ---------------------------------------------------------------------------
# .env / 設定
# ---------------------------------------------------------------------------
def load_env() -> None:
    """把專案根目錄的 .env 載入 os.environ（已存在的環境變數不覆蓋）。"""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def env(name: str, default: str = "") -> str:
    val = os.environ.get(name)
    return val if val not in (None, "") else default


def load_config() -> dict:
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    # 允許用環境變數覆蓋聯絡資訊，避免把私人資料寫進 repo
    brand = cfg.setdefault("brand", {})
    brand["contact_email"] = env("SENDER_EMAIL", env("SMTP_USER", brand.get("contact_email", "")))
    brand["sender_name"] = env("SENDER_NAME", brand.get("sender_name", "SiteCraft"))
    brand["sender_person"] = env("SENDER_PERSON", brand.get("sender_person", ""))
    brand["contact_line"] = env("CONTACT_LINE", brand.get("contact_line", ""))
    brand["contact_phone"] = env("CONTACT_PHONE", brand.get("contact_phone", ""))
    brand["demo_base_url"] = env("DEMO_BASE_URL", brand.get("demo_base_url", "")).rstrip("/")
    return cfg


def load_themes() -> dict:
    return json.loads(THEMES_FILE.read_text(encoding="utf-8"))


def pick_theme(themes: dict, *texts: str) -> tuple[str, dict]:
    """用類別/店名/查詢字串裡的關鍵字配主題；配不到就用 default。"""
    haystack = " ".join(t for t in texts if t).lower()
    for key, theme in themes.items():
        if key == "default":
            continue
        for kw in theme.get("keywords", []):
            if kw.lower() in haystack:
                return key, theme
    return "default", themes["default"]


# ---------------------------------------------------------------------------
# CSV 讀寫
# ---------------------------------------------------------------------------
def read_leads(path: Path = LEADS_FILE) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append({k: (row.get(k) or "") for k in LEAD_FIELDS})
        return rows


def write_leads(rows: list[dict], path: Path = LEADS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEAD_FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in LEAD_FIELDS})
    tmp.replace(path)


def append_sent_log(entry: dict, path: Path = SENT_LOG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SENT_LOG_FIELDS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow({k: entry.get(k, "") for k in SENT_LOG_FIELDS})


def find_lead(rows: list[dict], slug_or_place_id: str) -> dict | None:
    key = slug_or_place_id.strip()
    for row in rows:
        if row.get("slug") == key or row.get("place_id") == key:
            return row
    return None


# ---------------------------------------------------------------------------
# 日期 / 字串
# ---------------------------------------------------------------------------
def today() -> str:
    return date.today().isoformat()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def days_from_today(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def parse_day(s: str) -> date | None:
    s = (s or "").strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def make_slug(theme_key: str, place_id: str) -> str:
    """店名多為中文，URL 用 主題-短雜湊，例如 cafe-7f3a2c。"""
    digest = hashlib.sha1(place_id.encode("utf-8")).hexdigest()[:6]
    return f"{theme_key}-{digest}"


TW_ADDR_RE = re.compile(r"(?P<city>[^\s\d]{1,3}?[市縣])(?P<district>[^\s\d]{1,4}?[區鄉鎮市])")


def parse_tw_address(formatted: str) -> tuple[str, str]:
    """
    從 Google 的 formattedAddress 抓出縣市與鄉鎮市區。
    例：'403台灣台中市西區公益路100號' -> ('台中市', '西區')
    """
    s = (formatted or "").replace("台灣", "").replace("臺灣", "")
    m = TW_ADDR_RE.search(s)
    if not m:
        return "", ""
    return m.group("city"), m.group("district")


def phone_href(phone: str) -> str:
    """'04 2222 3333' -> 'tel:+886422223333'；空值回傳空字串。"""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if digits.startswith("886"):
        return f"tel:+{digits}"
    if digits.startswith("0"):
        return f"tel:+886{digits[1:]}"
    return f"tel:{digits}"


def website_status(uri: str, social_domains: list[str]) -> str:
    """none = 沒有網站；social = 只有 FB/IG/LINE 之類；real = 真的有官網。"""
    uri = (uri or "").strip()
    if not uri:
        return "none"
    host = urlparse(uri if "://" in uri else f"https://{uri}").netloc.lower()
    for d in social_domains:
        if d.lower() in host:
            return "social"
    return "real"


def demo_url_for(slug: str, cfg: dict) -> str:
    base = cfg["brand"].get("demo_base_url", "")
    return f"{base}/{slug}/" if base else f"sites/{slug}/index.html"


def fmt_rating(rating: str) -> str:
    try:
        return f"{float(rating):.1f}"
    except (TypeError, ValueError):
        return ""


def stars(rating: str) -> str:
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return ""
    full = int(round(r))
    return "" * full + "" * (5 - full)
