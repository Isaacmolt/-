#!/usr/bin/env python3
"""
SiteCraft — 第 2 步：為每家店產生一頁式網站（示範版 / 正式版）
=================================================================
用法：
    python sitecraft/build_site.py                      # 所有 status=new 的店家 → sites/<slug>/，狀態改 demo_ready
    python sitecraft/build_site.py --slug cafe-7f3a2c    # 只做指定店家（可重複）
    python sitecraft/build_site.py --rebuild             # 模板改了：重做所有已產生的網站（不改狀態）
    python sitecraft/build_site.py --ai-copy             # 用 Claude 幫每家店寫專屬文案（需 ANTHROPIC_API_KEY）
    python sitecraft/build_site.py --sample              # 用 data/leads.sample.csv 產生 3 個範例站（demo-*）
    python sitecraft/build_site.py --index               # 只重做 sites/index.html 作品集頁

每個網站資料夾：
    sites/<slug>/index.html     單一檔案、無外部依賴（字型除外），可直接交付
    sites/<slug>/content.json   可手動編輯的文案與聯絡資訊；店家付款後把真實內容填進去再 rebuild 即可
    sites/<slug>/img/           店家照片放這裡，並在 content.json 的 gallery 列出檔名

正式版（拿掉示範橫幅）由 crm.py publish <slug> 產生。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import (
    LEADS_FILE, SAMPLE_LEADS_FILE, SITES_DIR, TEMPLATES_DIR, demo_url_for, env, fmt_rating,
    load_config, load_env, load_themes, phone_href, read_leads, stars, write_leads,
)

ACTIVE_STATUSES = {"demo_ready", "contacted", "followup_1", "followup_2", "replied", "won", "delivered"}
WEEKDAY_LABELS = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
SCHEMA_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR / "site")),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True, lstrip_blocks=True,
)


# ---------------------------------------------------------------------------
# 文案：content.json > Claude > 主題預設
# ---------------------------------------------------------------------------
def default_copy(lead: dict, theme: dict) -> dict:
    fill = {"name": lead["name"], "city": lead["city"], "district": lead["district"] or "在地"}
    idx = int(hashlib.sha1(lead["place_id"].encode()).hexdigest()[:2], 16) % len(theme["taglines"])
    about = theme["about"].format(**fill)
    return {
        "tagline": theme["taglines"][idx].format(**fill),
        "about": [about],
        "highlights": list(theme["highlights"]),
        "services": [dict(s) for s in theme["services"]],
    }


COPY_SCHEMA = {
    "type": "object",
    "properties": {
        "tagline": {"type": "string", "description": "一句標語，12 個中文字以內，不要用驚嘆號"},
        "about": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2,
                  "description": "兩段關於我們，每段 60～90 個中文字，口吻像老闆自己說話，不誇大、不編造得獎或年資"},
        "highlights": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3,
                       "description": "三個特色，每個 8 個中文字以內"},
        "services": {
            "type": "array", "minItems": 4, "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "icon": {"type": "string", "description": "一個 emoji"},
                    "title": {"type": "string", "description": "服務名稱，6 字以內"},
                    "desc": {"type": "string", "description": "一句說明，25 字以內"},
                },
                "required": ["icon", "title", "desc"], "additionalProperties": False,
            },
        },
    },
    "required": ["tagline", "about", "highlights", "services"],
    "additionalProperties": False,
}

AI_SYSTEM = (
    "你是替台灣在地小店寫官網文案的寫手。用繁體中文（台灣用語），語氣真誠、具體、不浮誇，"
    "像老闆親口介紹自己的店。只能根據提供的資料寫，不可以編造得獎、年資、名人推薦或任何無法證實的事。"
    "不要出現「我們致力於」「極致」「頂級」這類空話。"
)


def ai_copy(lead: dict, theme: dict) -> dict | None:
    """用 Claude 產生專屬文案；任何失敗都回 None 讓呼叫端退回預設文案。"""
    try:
        import anthropic
    except ImportError:
        print("    ! 未安裝 anthropic 套件（pip install anthropic），改用預設文案")
        return None
    if not env("ANTHROPIC_API_KEY") and not env("ANTHROPIC_AUTH_TOKEN"):
        print("    ! 沒有 ANTHROPIC_API_KEY，改用預設文案")
        return None

    hours = ""
    if lead.get("hours_json"):
        try:
            hours = "；".join(json.loads(lead["hours_json"]).get("weekday", []))
        except ValueError:
            pass
    prompt = (
        f"店名：{lead['name']}\n類別：{lead['category'] or theme['label']}\n"
        f"地點：{lead['city']}{lead['district']}（{lead['address']}）\n"
        f"Google 評分：{lead['rating'] or '無'}（{lead['review_count'] or 0} 則評論）\n"
        f"營業時間：{hours or '未知'}\n"
        f"參考主題（可調整）：特色 {theme['highlights']}；服務 {[s['title'] for s in theme['services']]}\n\n"
        "請依 schema 輸出這家店的官網文案。"
    )
    client = anthropic.Anthropic()
    kwargs = dict(
        model="claude-opus-5-5",
        max_tokens=2048,
        system=AI_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": COPY_SCHEMA}},
    )
    try:
        try:
            # 開啟伺服器端安全分類器的自動備援（refusal 時換模型重跑同一請求）
            resp = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        except (TypeError, anthropic.BadRequestError):
            resp = client.messages.create(**kwargs)
    except anthropic.RateLimitError:
        print("    ! Claude 流量限制，改用預設文案")
        return None
    except anthropic.APIStatusError as exc:
        print(f"    ! Claude API 錯誤 {exc.status_code}，改用預設文案")
        return None
    except anthropic.APIConnectionError:
        print("    ! 無法連線 Claude API，改用預設文案")
        return None

    if resp.stop_reason == "refusal":
        print("    ! Claude 拒絕此請求，改用預設文案")
        return None
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except ValueError:
        print("    ! Claude 回傳不是合法 JSON，改用預設文案")
        return None
    return data


def load_or_make_content(lead: dict, theme: dict, site_dir: Path, use_ai: bool, refresh: bool) -> dict:
    """content.json 是唯一真相；沒有就用 Claude 或主題預設建立一份。"""
    cj = site_dir / "content.json"
    if cj.exists() and not refresh:
        try:
            content = json.loads(cj.read_text(encoding="utf-8"))
        except ValueError:
            print(f"    ! {cj} 不是合法 JSON，將重建")
            content = {}
        if content:
            return content

    copy = (ai_copy(lead, theme) if use_ai else None) or default_copy(lead, theme)
    content = {
        "_說明": "改這個檔案再執行 build_site.py --slug <slug> --rebuild 就會更新網站。gallery 放 img/ 裡的檔名。",
        "name": lead["name"],
        "tagline": copy["tagline"],
        "about": copy["about"],
        "highlights": copy["highlights"],
        "services": copy["services"],
        "phone": lead.get("phone", ""),
        "line_url": lead.get("line_url", ""),
        "facebook_url": lead.get("facebook_url", ""),
        "instagram_url": lead.get("instagram_url", ""),
        "gallery": [],
    }
    site_dir.mkdir(parents=True, exist_ok=True)
    cj.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return content



# ---------------------------------------------------------------------------
# 版面素材：字型、名稱拆字、抽象圖、標語強調
# ---------------------------------------------------------------------------
FONT_MODES = {
    # 編輯感：襯線中文 + Fraunces；粗獷感：黑體 900 + Syne
    "editorial": {
        "url": "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=Noto+Serif+TC:wght@500;600;700&family=Noto+Sans+TC:wght@400;500;600;700&display=swap",
        "display": "Fraunces", "head": "Noto Serif TC", "weight": "600",
    },
    "bold": {
        "url": "https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=Noto+Sans+TC:wght@400;500;600;700;900&display=swap",
        "display": "Syne", "head": "Noto Sans TC", "weight": "800",
    },
}

CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def name_tokens(name: str) -> list[str]:
    """中文逐字、拉丁逐詞，給 hero 標題做進場動畫。"""
    tokens: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            tokens.append(buf)
            buf = ""

    for ch in name:
        if CJK.match(ch):
            flush()
            tokens.append(ch)
        elif ch.isspace():
            flush()
            if tokens and tokens[-1] != " ":
                tokens.append(" ")
        else:
            buf += ch
    flush()
    while tokens and tokens[-1] == " ":
        tokens.pop()
    return tokens


def name_lines(name: str) -> list[dict]:
    """店名拆成中文行（逐字）與拉丁行（逐詞），hero 標題各佔一行。"""
    lines: list[dict] = []
    for tok in name_tokens(name):
        if not tok.strip():
            continue
        kind = "zh" if CJK.match(tok) else "en"
        if not lines or lines[-1]["kind"] != kind:
            lines.append({"kind": kind, "tokens": []})
        lines[-1]["tokens"].append(tok)
    return lines


def split_statement(text: str) -> tuple[str, str, str]:
    """把標語裡的最後一個短句標成強調色（用標點切）。"""
    text = text.strip().rstrip("。")
    for sep in ("，", "、", "：", " "):
        if sep in text:
            pre, _, em = text.rpartition(sep)
            return pre + sep, em, ""
    return "", text, ""


def art_tiles(palette: dict, seed: str, motif: str = "", n: int = 6) -> list[str]:
    """
    示意圖是一套系統而不是隨機圖案：雙色底 + 該類別圖騰的三種尺度（滿版、特寫、重複圖樣），
    外加一張「相框」告訴老闆這裡會換成照片。同一家店每次產生都一樣。
    """
    from markupsafe import Markup
    rnd = random.Random(seed)
    p, pd, a, bg = palette["p"], palette["pd"], palette["a"], palette["bg"]
    soft, asoft = palette["p_soft"], palette["a_soft"]
    stroke = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'

    def g(tx, ty, sc, color, width, extra=""):
        return (f'<g transform="translate({tx} {ty}) scale({sc})" {stroke} stroke="{color}" '
                f'stroke-width="{width}" {extra}>{motif}</g>')

    specs = [
        # (ground colour, motif placement)
        (asoft, g(80, 30, 1.2, pd, 2.4)),                                   # 1 滿版主圖
        (p, g(-60, -40, 2.6, bg, 1.6, 'opacity=".9"')),                      # 2 特寫（高）
        (soft, '<rect x="36" y="30" width="328" height="240" rx="14" fill="none" stroke="' + pd + '" stroke-width="2" stroke-dasharray="8 8" opacity=".55"/>'
               + '<path d="M36 30L364 270M364 30L36 270" stroke="' + pd + '" stroke-width="1" opacity=".18"/>'
               + g(160, 110, .4, pd, 4, 'opacity=".75"')),                    # 3 相框
        (a, g(150, 90, 2.2, pd, 1.8, 'opacity=".85"')),                      # 4 特寫（右下）
        (soft, "".join(g(16 + i * 76, 10 + j * 76, .32, p, 5, 'opacity=".55"') for i in range(6) for j in range(5))),  # 5 圖樣（高）
        (pd, g(90, 40, 1.1, a, 2.6)),                                        # 6 深底主圖
    ]
    tiles = []
    for i in range(n):
        ground, art = specs[i % len(specs)]
        rot = rnd.randint(-6, 6)
        parts = [f'<svg class="art" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" aria-hidden="true">',
                 f'<rect width="400" height="300" fill="{ground}"/>']
        if i % 6 in (0, 3):
            parts.append(f'<circle cx="{rnd.randint(260, 330)}" cy="{rnd.randint(60, 120)}" r="{rnd.randint(70, 110)}" fill="{a if i % 6 == 0 else asoft}" opacity=".55"/>')
        parts.append(f'<g transform="rotate({rot} 200 150)">{art}</g>')
        parts.append("</svg>")
        tiles.append(Markup("".join(parts)))
    return tiles


MOTIFS_FILE = TEMPLATES_DIR.parent / "data" / "motifs.json"


def load_motifs() -> dict:
    return json.loads(MOTIFS_FILE.read_text(encoding="utf-8"))


LINE_OA = re.compile(r"line\.me/R/ti/p/(@[\w.-]+)")


def service_href(title: str, line_url: str, phone_href: str) -> str:
    """服務列的連結：LINE 官方帳號可帶預填訊息；否則退回 LINE 連結或電話；都沒有就不連。"""
    m = LINE_OA.search(line_url or "")
    if m:
        return f"https://line.me/R/oaMessage/{m.group(1)}/?{quote('想詢問：' + title)}"
    if line_url:
        return line_url
    return phone_href or ""


def statement_from(about: list[str], tagline: str) -> tuple[str, list[str]]:
    """關於我們的大標用介紹的第一句（不重複 hero 標語）；回傳 (大標, 其餘段落)。"""
    if not about:
        return tagline, []
    first = about[0]
    head, sep, rest = first.partition("。")
    if not sep or len(head) > 40:
        return tagline, about
    paras = ([rest] if rest.strip() else []) + about[1:]
    return head, paras


def closing_title(theme_key: str, name: str) -> str:
    return {
        "cafe": "今天，來喝一杯", "breakfast": "明天早餐，來這裡", "restaurant": "今晚，來這裡吃飯",
        "snack": "肚子餓了，就來", "hotpot": "今晚，吃鍋", "dessert": "給自己一點甜",
        "hair": "預約你的下一個樣子", "beauty": "把時間留給自己", "pet": "毛小孩，交給我們",
        "clinic": "預約看診", "gym": "從今天開始動", "florist": "把心意做成一束花",
        "auto": "車子有狀況，先打給我們", "education": "預約一堂免費試上", "wellness": "給身體一小時",
        "lodging": "下一趟，住這裡",
    }.get(theme_key, f"歡迎來到 {name}")


# ---------------------------------------------------------------------------
# 營業時間
# ---------------------------------------------------------------------------
def parse_hours(hours_json: str) -> tuple[list[dict], list[dict]]:
    if not hours_json:
        return [], []
    try:
        data = json.loads(hours_json)
    except ValueError:
        return [], []
    weekday = []
    for i, desc in enumerate(data.get("weekday", [])[:7]):
        parts = re.split(r"[:：]\s*", desc, maxsplit=1)
        label = parts[0].strip() if parts else WEEKDAY_LABELS[(i + 1) % 7]
        text = parts[1].strip() if len(parts) > 1 else desc
        closed = any(k in text for k in ("休息", "Closed", "closed", "公休"))
        # Google 的 weekdayDescriptions 從星期一開始；JS getDay() 星期日 = 0
        weekday.append({"day": (i + 1) % 7, "label": label, "text": text or "休息", "closed": closed})
    return weekday, data.get("periods", [])


def opening_hours_spec(periods: list[dict]) -> list[dict]:
    spec = []
    for p in periods:
        o, c = p.get("open") or {}, p.get("close") or {}
        if "day" not in o or "hour" not in o or "hour" not in c:
            continue
        spec.append({
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": SCHEMA_DAYS[o["day"] % 7],
            "opens": f"{o['hour']:02d}:{o.get('minute', 0):02d}",
            "closes": f"{c['hour']:02d}:{c.get('minute', 0):02d}",
        })
    return spec


# ---------------------------------------------------------------------------
# 組裝 + 渲染
# ---------------------------------------------------------------------------
def favicon_svg(color: str, initial: str) -> str:
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
           f"<rect width='64' height='64' rx='14' fill='{color}'/>"
           f"<text x='32' y='43' font-size='32' font-weight='700' font-family='Georgia,serif' fill='white' text-anchor='middle'>{initial}</text></svg>")
    return quote(svg, safe="")


# ---------------------------------------------------------------------------
# og:image（LINE / Facebook 分享卡）：1200x630 PNG，需要一個系統中文字型
# ---------------------------------------------------------------------------
CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
    "C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/msjhbd.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def find_cjk_font() -> str:
    for c in CJK_FONT_CANDIDATES:
        if Path(c).exists():
            return c
    try:
        import subprocess
        out = subprocess.run(["fc-list", ":lang=zh", "file"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            f = line.split(":")[0].strip()
            if f.lower().endswith((".ttf", ".ttc", ".otf")):
                return f
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def og_image(lead: dict, content: dict, theme: dict, out: Path) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    font_file = find_cjk_font()
    if not font_file:
        return False
    pal = theme["palette"]
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), _hex(pal["pd"]))
    px = img.load()
    c0, c1 = _hex(pal["p"]), _hex(pal["pd"])
    for y in range(H):
        f = y / H
        row = tuple(int(c0[i] * (1 - f) + c1[i] * f) for i in range(3))
        for x in range(W):
            px[x, y] = row
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    ac = _hex(pal["a"])
    od.ellipse((780, -140, 1380, 460), fill=ac + (70,))
    od.ellipse((900, 300, 1500, 900), fill=ac + (40,))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    d = ImageDraw.Draw(img)
    name = content.get("name") or lead["name"]
    size = 96 if len(name) <= 10 else 72 if len(name) <= 16 else 56
    big = ImageFont.truetype(font_file, size)
    mid = ImageFont.truetype(font_file, 34)
    small = ImageFont.truetype(font_file, 28)
    d.text((80, 96), f"{lead.get('category') or theme['label']}　{lead.get('city', '')}{lead.get('district', '')}", font=mid, fill=(255, 255, 255, 215))
    d.text((80, 170), name, font=big, fill=(255, 255, 255, 255))
    d.text((80, 170 + size + 28), content.get("tagline", ""), font=mid, fill=(255, 255, 255, 230))
    y = 500
    if lead.get("rating"):
        d.text((80, y), f"Google 評分 {fmt_rating(lead['rating'])}　{lead.get('review_count', '')} 則評論", font=small, fill=(255, 255, 255, 205))
        y += 42
    d.text((80, y), lead.get("address", ""), font=small, fill=(255, 255, 255, 180))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, "PNG", optimize=True)
    return True


def render_site(lead: dict, content: dict, cfg: dict, themes: dict, demo: bool, og_png: bool = False) -> str:
    theme = themes.get(lead.get("theme") or "default", themes["default"])
    brand = cfg["brand"]
    weekday_hours, periods = parse_hours(lead.get("hours_json", ""))
    today_idx = (date.today().weekday() + 1) % 7
    today_hours = next((h["text"] for h in weekday_hours if h["day"] == today_idx), "")
    url = lead.get("delivered_url") or lead.get("demo_url") or demo_url_for(lead["slug"], cfg)
    phone = content.get("phone") or lead.get("phone", "")
    name = content.get("name") or lead["name"]
    address = lead.get("address", "")
    maps_url = lead.get("maps_url") or f"https://www.google.com/maps/search/?api=1&query={quote(name + ' ' + address)}"
    about = content.get("about") or []
    if isinstance(about, str):
        about = [about]

    motifs = load_motifs()
    motif = motifs.get(lead.get("theme") or "default") or motifs["default"]
    imgs = [g for g in content.get("gallery", []) if g]
    arts = art_tiles(theme["palette"], lead["slug"], motif)
    gallery_items = []
    for i in range(max(len(imgs), 6) if imgs else 6):
        gallery_items.append({"img": imgs[i] if i < len(imgs) else "", "art": arts[i % len(arts)],
                              "tall": i % 3 == 1, "type": (not imgs) and i == 1})
    mode = FONT_MODES.get(theme.get("mode", "bold"), FONT_MODES["bold"])
    statement, about = statement_from(about, content.get("tagline", ""))
    pre, em, post = split_statement(statement)
    line_url = content.get("line_url", "")
    services = []
    for s_ in content.get("services", []):
        s_ = dict(s_)
        s_["href"] = service_href(s_.get("title", ""), line_url, phone_href(phone))
        services.append(s_)
    initial = next((ch for ch in name if ch.strip()), "S")
    city_district = f"{lead.get('city', '')}{lead.get('district', '')}"
    address_short = address
    if city_district and city_district in address:
        address_short = address.split(city_district, 1)[1] or address

    jsonld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
        "description": content.get("tagline", ""),
        "url": url,
        "telephone": phone,
        "address": {"@type": "PostalAddress", "streetAddress": address,
                    "addressLocality": lead.get("district", ""), "addressRegion": lead.get("city", ""),
                    "addressCountry": "TW"},
        "openingHoursSpecification": opening_hours_spec(periods),
    }
    if lead.get("rating") and lead.get("review_count"):
        jsonld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": fmt_rating(lead["rating"]),
                                     "reviewCount": lead["review_count"]}
    same_as = [u for u in (content.get("facebook_url"), content.get("instagram_url"), maps_url) if u]
    if same_as:
        jsonld["sameAs"] = same_as

    contact_href = ""
    if brand.get("contact_email"):
        contact_href = f"mailto:{brand['contact_email']}?subject={quote(f'{name} 網站上線')}"
    elif brand.get("contact_line", "").startswith("http"):
        contact_href = brand["contact_line"]

    show_credit = demo or brand.get("show_credit_on_final_site", True)
    b = {
        "name": name, "slug": lead["slug"], "url": url,
        "category": lead.get("category") or theme["label"],
        "city": lead.get("city", ""), "district": lead.get("district", ""),
        "address": address, "phone": phone, "phone_href": phone_href(phone),
        "line_url": content.get("line_url", ""), "facebook_url": content.get("facebook_url", ""),
        "instagram_url": content.get("instagram_url", ""),
        "rating": fmt_rating(lead.get("rating", "")), "stars": stars(lead.get("rating", "")),
        "review_count": lead.get("review_count", ""), "maps_url": maps_url,
        "embed_url": f"https://www.google.com/maps?q={quote(name + ' ' + address)}&hl=zh-TW&z=16&output=embed",
        "tagline": content.get("tagline", ""), "about_paragraphs": about,
        "highlights": content.get("highlights", []), "services": services,
        "services_linked": any(s_["href"] for s_ in services),
        "og_image": (url.rstrip("/") + "/og.png") if og_png else "",
        "gallery_items": gallery_items,
        "weekday_hours": weekday_hours, "periods": periods, "today_hours": today_hours,
        "jsonld": jsonld, "favicon_svg": favicon_svg(theme["palette"]["pd"], initial),
        "initial": initial, "name_tokens": name_tokens(name), "name_lines": name_lines(name), "address_short": address_short,
        "mode": theme.get("mode", "bold"),
        "fonts_url": mode["url"], "font_display": mode["display"], "font_head": mode["head"], "head_weight": mode["weight"],
        "statement_pre": pre, "statement_em": em, "statement_post": post,
        "closing_title": closing_title(lead.get("theme") or "default", name),
        "year": date.today().year,
        "credit": brand["sender_name"] if show_credit else "",
        "credit_url": (brand.get("demo_base_url") or "") + "/",
        "sitecraft_name": brand["sender_name"], "sitecraft_contact_href": contact_href,
        "price_twd": brand.get("price_twd", 860),
    }
    tpl = _env.get_template("onepage.html.j2")
    from markupsafe import Markup
    return minify_css(tpl.render(b=b, t={**theme["palette"], "word": theme.get("word", "LOCAL"), "motif": Markup(motif)}, demo=demo))


CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def minify_css(html: str) -> str:
    """只壓縮 <style> 區塊：拿掉註解與行首縮排、合併換行（字串內的空白不動）。"""
    def _min(m: re.Match) -> str:
        css = CSS_COMMENT.sub("", m.group(2))
        css = "\n".join(line.strip() for line in css.splitlines() if line.strip())
        css = css.replace("{\n", "{").replace("\n}", "}").replace(";\n", ";").replace("}\n", "}")
        return m.group(1) + css + m.group(3)
    return re.sub(r"(<style>)(.*?)(</style>)", _min, html, flags=re.S)


def build_one(lead: dict, cfg: dict, themes: dict, *, demo: bool = True, use_ai: bool = False,
              refresh_copy: bool = False) -> Path:
    site_dir = SITES_DIR / lead["slug"]
    site_dir.mkdir(parents=True, exist_ok=True)
    theme = themes.get(lead.get("theme") or "default", themes["default"])
    content = load_or_make_content(lead, theme, site_dir, use_ai, refresh_copy)
    og_ok = og_image(lead, content, theme, site_dir / "og.png")
    html = render_site(lead, content, cfg, themes, demo=demo, og_png=og_ok)
    (site_dir / "index.html").write_text(html, encoding="utf-8")
    return site_dir / "index.html"


def build_index(cfg: dict, themes: dict) -> Path:
    """sites/index.html 作品集：所有已產生網站（含範例）。"""
    rows = read_leads(LEADS_FILE) + read_leads(SAMPLE_LEADS_FILE)
    sites, seen = [], set()
    for r in rows:
        if not r.get("slug") or r["slug"] in seen or not (SITES_DIR / r["slug"] / "index.html").exists():
            continue
        if r.get("status") in ("lost", "opted_out", "has_website", "skipped"):
            continue
        seen.add(r["slug"])
        theme = themes.get(r.get("theme") or "default", themes["default"])
        sites.append({"slug": r["slug"], "name": r["name"], "category": r.get("category") or theme["label"],
                      "city": r.get("city", ""), "district": r.get("district", ""), "word": theme.get("word", "LOCAL"),
                      "p": theme["palette"]["p"], "pd": theme["palette"]["pd"],
                      "live": r.get("status") == "delivered"})
    sites.sort(key=lambda s: (not s["live"], s["name"]))
    brand = cfg["brand"]
    html = _env.get_template("index.html.j2").render(
        brand=brand["sender_name"], price_twd=brand.get("price_twd", 860),
        hosting_years=brand.get("hosting_years_included", 1), sites=sites,
        year=date.today().year, contact=brand.get("contact_email") or brand.get("contact_line") or "")
    SITES_DIR.mkdir(parents=True, exist_ok=True)
    out = SITES_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="為名單裡的店家產生一頁式網站")
    ap.add_argument("--slug", action="append", help="只處理指定 slug（可重複）")
    ap.add_argument("--rebuild", action="store_true", help="重做所有已產生網站的 index.html（模板更新用）")
    ap.add_argument("--ai-copy", action="store_true", help="用 Claude 寫文案（否則用主題預設）")
    ap.add_argument("--refresh-copy", action="store_true", help="忽略既有 content.json、重新產生文案")
    ap.add_argument("--sample", action="store_true", help="用 data/leads.sample.csv 產生範例站")
    ap.add_argument("--index", action="store_true", help="只重做作品集頁 sites/index.html")
    args = ap.parse_args()

    load_env()
    cfg = load_config()
    themes = load_themes()

    if args.index:
        print("[index] 作品集 →", build_index(cfg, themes))
        return

    leads_path = SAMPLE_LEADS_FILE if args.sample else LEADS_FILE
    rows = read_leads(leads_path)
    if not rows:
        sys.exit(f"{leads_path} 沒有資料。先跑 find_leads.py，或用 --sample 看範例。")

    if args.slug:
        targets = [r for r in rows if r["slug"] in set(args.slug)]
        missing = set(args.slug) - {r["slug"] for r in targets}
        if missing:
            print("! 找不到 slug：", ", ".join(sorted(missing)))
    elif args.rebuild:
        targets = [r for r in rows if r["status"] in ACTIVE_STATUSES or args.sample]
    else:
        targets = [r for r in rows if r["status"] == "new" or (args.sample and r["status"] != "delivered")]

    if not targets:
        print("沒有需要產生的店家（status=new）。用 --rebuild 重做既有網站、或 --slug 指定。")
        return

    print(f"[build]  產生 {len(targets)} 個網站{'（Claude 文案）' if args.ai_copy else ''}…")
    changed = False
    for lead in targets:
        if not lead.get("slug"):
            continue
        demo = lead["status"] != "delivered"
        out = build_one(lead, cfg, themes, demo=demo, use_ai=args.ai_copy, refresh_copy=args.refresh_copy)
        if lead["status"] == "new":
            lead["status"] = "demo_ready"
            changed = True
        if not lead.get("demo_url"):
            lead["demo_url"] = demo_url_for(lead["slug"], cfg)
            changed = True
        print(f"  + {lead['name']:<16} {lead.get('theme', ''):<10} → {out.relative_to(SITES_DIR.parent)}")

    if changed and not args.sample:
        write_leads(rows, leads_path)
    build_index(cfg, themes)
    print()
    print(f"[ok] 完成。推上 GitHub 後網址為 {cfg['brand']['demo_base_url']}/<slug>/")
    if not args.sample:
        print("下一步：python sitecraft/crm.py due              # 看哪些店家還缺 email")
        print("        python sitecraft/send_outreach.py --stage first   # 預覽第一封信")


if __name__ == "__main__":
    main()
