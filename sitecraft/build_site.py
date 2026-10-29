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
    sites/<slug>/index.html     單一檔案、無外部依賴，字型切好放在 sites/<slug>/fonts/，可直接交付
    sites/<slug>/content.json   可手動編輯的文案與聯絡資訊；店家付款後把真實內容填進去再 rebuild 即可
    sites/<slug>/img/           店家照片放這裡，並在 content.json 的 gallery 列出檔名

正式版（拿掉示範橫幅）由 crm.py publish <slug> 產生。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import random
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

import fonts as fontkit
import scenes

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
        "statement": theme.get("statement", "").format(**fill),
        "about": [about],
        "highlights": list(theme["highlights"]),
        "services": [dict(s) for s in theme["services"]],
    }


COPY_SCHEMA = {
    "type": "object",
    "properties": {
        "tagline": {"type": "string", "description": "一句標語，12 個中文字以內，不要用驚嘆號"},
        "statement": {"type": "string", "description": "關於我們的大標，14～22 個中文字，用一個逗號分成兩段，後段是重點；不要出現店名"},
        "about": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2,
                  "description": "兩段關於我們，每段 60～90 個中文字，口吻像老闆自己說話，不誇大、不編造得獎或年資"},
        "highlights": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3,
                       "description": "三個特色，每個 8 個中文字以內"},
        "services": {
            "type": "array", "minItems": 4, "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "服務名稱，6 字以內"},
                    "desc": {"type": "string", "description": "一句說明，25 字以內"},
                },
                "required": ["title", "desc"], "additionalProperties": False,
            },
        },
    },
    "required": ["tagline", "statement", "about", "highlights", "services"],
    "additionalProperties": False,
}

AI_SYSTEM = (
    "你是替台灣在地小店寫官網文案的寫手。用繁體中文（台灣用語），語氣真誠、具體、不浮誇，"
    "像老闆親口介紹自己的店。只能根據提供的資料寫，不可以編造得獎、年資、名人推薦或任何無法證實的事。"
    "不要出現「我們致力於」「極致」「頂級」這類空話。不要使用任何 emoji 或表情符號。"
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


EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0F\u200D]")


def clean_content(content: dict) -> dict:
    """文案一律不放 emoji：拿掉舊版的 services[].icon，所有字串去掉表情符號。"""
    def walk(v):
        if isinstance(v, str):
            return EMOJI_RE.sub("", v).strip() if EMOJI_RE.search(v) else v
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items() if k != "icon"}
        return v
    return walk(content)


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
            cleaned = clean_content(content)
            if (lead.get("theme") or "") == "pet":
                cleaned = pet_words(cleaned)
            if cleaned != content:
                cj.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
            return cleaned

    copy = clean_content((ai_copy(lead, theme) if use_ai else None) or default_copy(lead, theme))
    if (lead.get("theme") or "") == "pet":
        copy = pet_words(copy)
    content = {
        "_說明": "改這個檔案再執行 build_site.py --slug <slug> --rebuild 就會更新網站。gallery 放 img/ 裡的檔名。",
        "name": lead["name"],
        "tagline": copy["tagline"],
        "statement": copy.get("statement", ""),
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
        "url": "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=Noto+Serif+TC:wght@600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap",
        "display": "Fraunces", "head": "Noto Serif TC", "weight": "600",
    },
    "bold": {
        "url": "https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Noto+Sans+TC:wght@400;500;700;900&display=swap",
        "display": "Syne", "head": "Noto Sans TC", "weight": "800",
    },
    # 清爽感：Space Grotesk + 黑體 600，診所、教室、寵物等
    "mono": {
        "url": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700&display=swap",
        "display": "Space Grotesk", "head": "Noto Sans TC", "weight": "600",
    },
}

ADDR_NO = re.compile(r"(\d+(?:之\d+)?號(?:\d+樓)?(?:之\d+)?)")


ADDR_PREFIX = re.compile(r"^\s*\d{3,6}\s*(台灣|臺灣)?\s*")


def address_display(address: str) -> str:
    """畫面上的地址不放郵遞區號與「台灣」（複製地址仍用完整版）。"""
    return ADDR_PREFIX.sub("", address or "").strip() or (address or "")


def address_html(address: str, city: str, district: str):
    """地址：只在「市」「區」之後允許換行（<wbr>，搭配 keep-all），門牌號與樓層不拆（.nb）。"""
    from markupsafe import Markup, escape
    address = address_display(address)
    out = ""
    rest = address
    if city and district and f"{city}{district}" in address:
        pre, _, rest = address.partition(f"{city}{district}")
        out += str(escape(pre + city)) + "<wbr>" + str(escape(district)) + "<wbr>"
    elif district and district in address:
        pre, _, rest = address.partition(district)
        out += str(escape(pre + district)) + "<wbr>"
    out += ADDR_NO.sub(lambda m: f'<span class="nb">{escape(m.group(1))}</span>', str(escape(rest)))
    return Markup(out)

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


NAME_WORDS = sorted("""工作室 咖啡館 咖啡廳 咖啡 早午餐 早餐 餐廳 小吃 麵館 麵店 火鍋 鍋物 甜點 烘焙 蛋糕 美髮 髮型 髮廊 沙龍 設計 美容 美甲
美睫 寵物 動物 醫院 診所 牙醫 健身 瑜珈 花店 花藝 汽車 機車 保養 維修 補習班 教室 書院 按摩 養生 民宿 旅店 商行 小館 食堂 生活 手作""".split(), key=len, reverse=True)


def cjk_groups(chars: list[str]) -> list[list[str]]:
    """把店名的中文字分成不可拆的詞組：「的」之後、常見行業詞前後才可以換行。"""
    text = "".join(chars)
    cuts = set()
    i = 0
    while i < len(text):
        hit = next((w for w in NAME_WORDS if text.startswith(w, i)), None)
        if hit:
            cuts.update((i, i + len(hit)))
            i += len(hit)
            continue
        if text[i] == "的":
            cuts.add(i + 1)
        i += 1
    cuts = sorted(c for c in cuts if 0 < c < len(text))
    groups, last = [], 0
    for c in cuts + [len(text)]:
        if c > last:
            groups.append(chars[last:c])
            last = c
    return groups


def name_len_units(name: str) -> float:
    """店名最長一行的「全形字數」，拉丁字母約算半形，用來依欄寬縮放標題。"""
    best = 1.0
    for line in name_lines(name):
        units = sum(1.0 if line["kind"] == "zh" else 0.55 * len(tok) for tok in line["tokens"]) + (0.3 * (len(line["tokens"]) - 1) if line["kind"] == "en" else 0)
        best = max(best, units)
    return round(best, 2)


def split_statement(text: str) -> tuple[str, str, str]:
    """把標語裡的最後一個短句標成強調色（用標點切）。"""
    text = text.strip().rstrip("。")
    for sep in ("，", "、", "：", " "):
        if sep in text:
            pre, _, em = text.rpartition(sep)
            return pre + sep, em, ""
    return "", text, ""


def scene_tile(key: str, mset: dict, name: str, seed: str, theme_key: str = "default") -> str:
    """相簿的場景插畫磚：吧台、街角（橫式）、窗邊（直式）。"""
    from markupsafe import Markup
    if key == "window":
        return Markup('<svg class="art scene" viewBox="0 0 300 400" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
                      f'{scenes.window(mset, drawable, hashlib.md5(seed.encode()).hexdigest()[:6])}</svg>')
    body = scenes.interior(mset, drawable, theme_key) if key == "counter" else scenes.street(mset, name, drawable, seed, theme_key)
    return Markup(f'<svg class="art scene" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" aria-hidden="true">{body}</svg>')


def map_art(seed: str) -> str:
    """地圖卡的示意街廓：幾條主要道路、巷弄與街區，圖釘在中央（每家店不同、每次一樣）。"""
    from markupsafe import Markup
    rnd = random.Random(seed + "map")
    roads, lanes, blocks = [], [], []
    for y in (rnd.randint(60, 90), rnd.randint(170, 200)):
        tilt = rnd.randint(-14, 14)
        roads.append(f'<path d="M-20 {y - tilt}L420 {y + tilt}"/>')
    for x in (rnd.randint(70, 110), rnd.randint(250, 300)):
        tilt = rnd.randint(-18, 18)
        roads.append(f'<path d="M{x - tilt} -20L{x + tilt} 320"/>')
    for _ in range(5):
        x, y = rnd.randint(0, 400), rnd.randint(0, 300)
        lanes.append(f'<path d="M{x} {y}l{rnd.choice((-1, 1)) * rnd.randint(40, 90)} {rnd.randint(-30, 30)}"/>')
    for _ in range(4):
        x, y = rnd.randint(20, 340), rnd.randint(20, 240)
        blocks.append(f'<rect x="{x}" y="{y}" width="{rnd.randint(30, 60)}" height="{rnd.randint(22, 44)}" rx="4"/>')
    return Markup(
        '<svg class="mapart" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
        f'<g class="mb">{"".join(blocks)}</g><g class="ml">{"".join(lanes)}</g><g class="mr">{"".join(roads)}</g></svg>')


def feature_cta(label: str, line_url: str) -> str:
    """沒有 LINE 時，招牌卡按鈕其實是撥電話：「LINE 訂位」改成「電話訂位」。"""
    if not line_url and label.startswith("LINE "):
        return "電話" + label[5:]
    return label


def pet_words(v):
    """寵物用「牠」：AI 文案或舊檔寫成「它」時一律改掉。"""
    if isinstance(v, str):
        return v.replace("它們", "牠們").replace("它", "牠")
    if isinstance(v, list):
        return [pet_words(x) for x in v]
    if isinstance(v, dict):
        return {k: pet_words(x) for k, x in v.items()}
    return v


def alt_line(theme: dict, tagline: str, fill: dict) -> str:
    """相簿直排標語用另一句（首屏已經有 tagline，不重複）。"""
    for t_ in theme.get("taglines", []):
        try:
            line = t_.format(**fill)
        except (KeyError, IndexError):
            continue
        if line and line != tagline and "{" not in line:
            return line
    return tagline


def vertical_columns(text: str) -> list[str]:
    """直排標語按標點分欄（標點留在前一欄）；沒有標點就整句一欄，交給前端斷詞平衡。"""
    cols, buf = [], ""
    for ch in text.strip().rstrip("。"):
        buf += ch
        if ch in "，、；：！？":
            cols.append(buf)
            buf = ""
    if buf:
        cols.append(buf)
    return cols[:3] or [text]


ACCENTS = {
    "circle": '<circle class="disc" cx="134" cy="76" r="58"/>',
    "arch": '<path class="disc" d="M88 156V80a48 48 0 0 1 96 0v76z"/>',
    "blob": '<path class="disc" d="M94 36c30-22 80-8 88 30s-8 70-46 72-70-14-68-46 0-38 26-56z"/>',
    "sun": '<path class="disc" d="M70 150a64 64 0 0 1 128 0z"/>',
    "square": '<rect class="disc" x="90" y="28" width="96" height="96" rx="20" transform="rotate(8 138 76)"/>',
    "halo": '<circle class="disc" cx="100" cy="102" r="80"/>',  # 寵物：整顆頭後面一個置中的圓，不半遮臉
    "mirror": '<path class="disc" d="M132 38h38a26 26 0 0 1 26 26v80h-90V64a26 26 0 0 1 26-26z"/>',  # 髮廊：鏡子的偏移色塊（印刷錯位感）
}
ACCENT_OF = {"cafe": "circle", "hair": "mirror", "pet": "halo", "breakfast": "sun", "restaurant": "circle", "snack": "blob",
             "hotpot": "sun", "dessert": "arch", "beauty": "blob", "clinic": "square", "gym": "square", "florist": "arch",
             "auto": "sun", "education": "square", "wellness": "blob", "lodging": "arch", "default": "circle"}


def scene_markup(mset: dict, key: str = "default") -> str:
    """hero 插畫：有 hero（多筆、兩種線寬、強調色填色）就用，沒有就用主圖騰；後面墊一塊這個類別專屬形狀的強調色。"""
    if mset.get("hero"):
        art = idle_classes(drawable(mset["hero"]), mset.get("hero_idle") or {"shapes": []})
    else:
        art = idle_classes(drawable(mset["a"]), mset.get("idle") or {"kind": "float", "shapes": [0]})
    return ACCENTS[ACCENT_OF.get(key, "circle")] + art


def print_scene(main: str, small: str = "", ground: bool = True) -> str:
    """雙色印刷感的插畫：先畫一層偏移的強調色填色，再疊上線條（線條會在捲到時描出來）。"""
    shapes = f'<g transform="translate(14 10) scale(.84)">{{m}}</g>' + (f'<g transform="translate(134 130) scale(.34)">{{s}}</g>' if small else "")
    tone = shapes.format(m=main, s=small)
    line = shapes.format(m=drawable(main), s=drawable(small) if small else "")
    return (f'<g class="tone" transform="translate(6 6)">{tone}</g>'
            + ('<path pathLength="1" d="M-6 196H214"/>' if ground else "") + f'<g class="ln">{line}</g>')


def photo_tall(src: str, site_dir: Path | None) -> bool | None:
    """本機照片看實際長寬決定直式或橫式；讀不到回 None（交給預設節奏）。"""
    if not site_dir or src.startswith(("http:", "https:", "data:")):
        return None
    try:
        from PIL import Image
        with Image.open(site_dir / src) as im:
            w, h = im.size
        return h > w * 1.05
    except Exception:  # noqa: BLE001
        return None


MOTIFS_FILE = TEMPLATES_DIR.parent / "data" / "motifs.json"


def load_motifs() -> dict:
    return json.loads(MOTIFS_FILE.read_text(encoding="utf-8"))


SHAPE_TAG = re.compile(r"<(path|circle|ellipse|rect)\b")


def drawable(markup: str) -> str:
    """每個形狀加 pathLength=1 與序號 --i，CSS 就能用 dasharray 做「依序畫出來」的動畫。"""
    n = 0

    def tag(mm: re.Match) -> str:
        nonlocal n
        n += 1
        return f'<{mm.group(1)} pathLength="1" style="--i:{n - 1}"'
    return SHAPE_TAG.sub(tag, markup)


def idle_classes(markup: str, idle: dict) -> str:
    """把指定序號的形狀加上閒置微動 class（蒸氣飄、刀刃開合、腳掌脈動）；原本有 class 就合併。"""
    kind, shapes = idle.get("kind", "float"), set(idle.get("shapes", []))
    n = -1

    def tag(mm: re.Match) -> str:
        nonlocal n
        n += 1
        el = mm.group(0)
        if n not in shapes:
            return el
        add = f"idle idle-{kind}"
        cm = re.search(r"""class=(['"])(.*?)\1""", el)
        if cm:
            return el[:cm.start()] + f'class="{cm.group(2)} {add}"' + el[cm.end():]
        return el[:-2] + f' class="{add}"/>' if el.endswith("/>") else el[:-1] + f' class="{add}">'
    return re.sub(r"<(?:path|circle|ellipse|rect)\b[^>]*>", tag, markup)


def _lum(c: str) -> float:
    r, g, bb = (int(c.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * bb


def _mix(c1: str, c2: str, w: float) -> str:
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b_ = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(a[i] * w + b_[i] * (1 - w)) for i in range(3))


LINE_OA = re.compile(r"line\.me/R/ti/p/(@[\w.-]+)")


def service_href(title: str, line_url: str, phone_href: str) -> str:
    """服務列的連結：LINE 官方帳號可帶預填訊息；否則退回 LINE 連結或電話；都沒有就不連。"""
    m = LINE_OA.search(line_url or "")
    if m:
        return f"https://line.me/R/oaMessage/{m.group(1)}/?{quote('想詢問：' + title)}"
    if line_url:
        return line_url
    return phone_href or ""


def about_opening(text: str, name: str, loc: str) -> str:
    """介紹第一句不再用「店名 位於某區，」的公式：店名已經在頁面上出現很多次，改用「我們」開頭。"""
    if not text or not loc:
        return text
    for nm in {name, name.replace(" ", "")}:
        for head, repl in ((f"{nm} 位於{loc}，是", f"在{loc}，我們是"), (f"{nm}位於{loc}，是", f"在{loc}，我們是"),
                           (f"{nm} 位於{loc}，提供", f"我們在{loc}提供"), (f"{nm}位於{loc}，提供", f"我們在{loc}提供"),
                           (f"{nm} 位於{loc}，", f"在{loc}，"), (f"{nm}位於{loc}，", f"在{loc}，"),
                           (f"{nm} 是{loc}", f"我們是{loc}"), (f"{nm}是{loc}", f"我們是{loc}")):
            if text.startswith(head):
                return repl + text[len(head):]
    return text


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


def signature_block(theme: dict, content: dict, services: list[dict]) -> dict | None:
    """每個類別一個招牌區塊：餐飲類把第一項服務做成「今日推薦」，服務類是三個步驟。content.json 可以覆寫。"""
    sig = content.get("signature") or theme.get("signature")
    if not sig:
        return None
    if sig.get("kind") == "feature":
        if not services:
            return None
        return {"kind": "feature", "label": sig.get("label", "招牌"), "item": services[0]}
    steps = [x for x in sig.get("steps", []) if x.get("title")][:3]
    return {"kind": "steps", "title": sig.get("title", ""), "steps": steps} if steps else None


def closing_closed(theme_key: str) -> str:
    """休息中時，結尾大標不要說「今天」「今晚」。"""
    return {"cafe": "下次，來喝一杯", "restaurant": "下次，來這裡吃飯", "hotpot": "下次，來吃鍋",
            "gym": "下次來，從那天開始動"}.get(theme_key, "")


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
        text = re.sub(r"\s*,\s*", "、", text)
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


VOICE_OG = {
    # 分享預覽圖用同一套字型語氣：中文行、英文行（字型檔, 軸設定）
    "editorial": (("NotoSerifTC[wght].ttf", {"Weight": 600}), ("Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", {"Optical Size": 96, "Weight": 400, "Softness": 0, "Wonky": 0})),
    "bold": (("NotoSansTC[wght].ttf", {"Weight": 800}), ("Syne[wght].ttf", {"Weight": 700})),
    "mono": (("NotoSansTC[wght].ttf", {"Weight": 600}), ("SpaceGrotesk[wght].ttf", {"Weight": 500})),
}


def _voice_font(spec, size):
    """變數字型設定軸；檔案不在就回 None。"""
    from PIL import ImageFont
    import fonts as fontkit
    name, axes = spec
    path = fontkit.FONT_DIR / name
    if not path.exists() and not fontkit.ensure_sources({name}, log=lambda *_: None):
        return None
    try:
        f = ImageFont.truetype(str(path), size)
        order = [a["name"].decode() if isinstance(a, dict) else a.decode() for a in f.get_variation_axes()]
        f.set_variation_by_axes([axes.get(n, 0) for n in order])
        return f
    except Exception:  # noqa: BLE001
        return None


def og_photo(content: dict, site_dir: Path):
    """有老闆的照片就用第一張，裁成拱門框放在分享圖右側。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    gallery = [g for g in content.get("gallery", []) if g]
    if not gallery:
        return None
    src = gallery[0] if "/" in gallery[0] else f"img/{gallery[0]}"
    try:
        im = Image.open(site_dir / src).convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    w, h = 360, 450
    r = im.width / im.height
    if r > w / h:
        nw = int(im.height * w / h); im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:
        nh = int(im.width * h / w); im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    im = im.resize((w, h))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, w // 2, w, h), radius=18, fill=255)
    md.ellipse((0, 0, w, w), fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def og_art(lead: dict, pal: dict):
    """分享圖右側畫上這一類的首屏插畫（需要 cairosvg；沒有就只留強調色圓）。"""
    try:
        import io
        import cairosvg
        from PIL import Image
    except Exception:  # noqa: BLE001
        return None
    mset = load_motifs().get(lead.get("theme") or "default") or load_motifs()["default"]
    body = mset.get("hero") or mset["a"]
    a = pal["a"]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 220 220" width="500" height="500">'
           '<style>*{fill:none;stroke:#fff;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round;stroke-opacity:.82}'
           f'.fine{{stroke-width:.85}}.acc{{fill:{a};stroke:none}}.acc2{{fill:{a};fill-opacity:.35}}</style>{body}</svg>')
    try:
        png = cairosvg.svg2png(bytestring=svg.encode("utf-8"))
        return Image.open(io.BytesIO(png)).convert("RGBA")
    except Exception:  # noqa: BLE001
        return None


def og_image(lead: dict, content: dict, theme: dict, out: Path) -> bool:
    """LINE / FB 分享預覽圖（1200×630）：用網站同一套字型語氣與主色，圓形強調色、地址不含郵遞區號。"""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        return False
    pal = theme["palette"]
    mode = theme.get("mode", "bold")
    name = content.get("name") or lead["name"]
    lines = name_lines(name)
    zh = "".join(lines[0]["tokens"]) if lines and lines[0]["kind"] == "zh" else ""
    en = " ".join(next((ln["tokens"] for ln in lines if ln["kind"] == "en"), []))
    spec_zh, spec_en = VOICE_OG.get(mode, VOICE_OG["bold"])
    base = find_cjk_font()
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), _hex(pal["pd"]))
    d0 = ImageDraw.Draw(img)
    c0, c1 = _hex(pal["p"]), _hex(pal["pd"])
    for y in range(H):
        f = min(1.0, y / (H * .9))
        d0.line([(0, y), (W, y)], fill=tuple(int(c0[i] * (1 - f) + c1[i] * f) for i in range(3)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    ac = _hex(pal["a"])
    gd.ellipse((800, 60, 1160, 420), fill=ac + (150,))
    glow = glow.filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    photo = og_photo(content, out.parent)
    if photo is not None:
        img.alpha_composite(photo, (W - 80 - photo.width, (H - photo.height) // 2 - 20))
    else:
        art = og_art(lead, pal)
        if art is not None:
            img.alpha_composite(art, (700, 40))
    d = ImageDraw.Draw(img)
    avail = 600
    zh_lines, zh_size, f_zh = [zh] if zh else [], 128, None
    for size in (128, 112, 100, 90, 80, 72):
        f_zh = _voice_font(spec_zh, size) or (ImageFont.truetype(base, size) if base else None)
        zh_size = size
        if not zh or (f_zh and f_zh.getlength(zh) <= avail):
            break
    if zh and f_zh and f_zh.getlength(zh) > avail:
        groups = ["".join(g) for g in cjk_groups(list(zh))]
        best = min(range(1, len(groups)), key=lambda i: abs(len("".join(groups[:i])) - len("".join(groups[i:]))), default=1)
        zh_lines = ["".join(groups[:best]), "".join(groups[best:])]
        for size in (100, 90, 80, 72, 64, 56):
            f_zh = _voice_font(spec_zh, size) or (ImageFont.truetype(base, size) if base else None)
            zh_size = size
            if f_zh and all(f_zh.getlength(t) <= avail for t in zh_lines):
                break
    f_en = None
    for size in (64, 56, 48, 40, 34):
        f_en = _voice_font(spec_en, size) or (ImageFont.truetype(base, size) if base else None)
        if not en or (f_en and f_en.getlength(en) <= avail):
            break
    f_small = _voice_font(("NotoSansTC[wght].ttf", {"Weight": 500}), 30) or (ImageFont.truetype(base, 30) if base else None)
    f_tag = _voice_font(spec_zh if mode == "editorial" else ("NotoSansTC[wght].ttf", {"Weight": 400}), 40) or f_small
    if not (f_zh and f_small):
        return False
    white = (255, 255, 255, 255)
    eyebrow = f"{lead.get('category') or theme['label']}　{lead.get('city', '')}{lead.get('district', '')}"
    d.line([(80, 112), (130, 112)], fill=(255, 255, 255, 200), width=2)
    d.text((148, 94), eyebrow, font=f_small, fill=(255, 255, 255, 220))
    y = 150
    if zh:
        for t in zh_lines:
            d.text((76, y), t, font=f_zh, fill=white)
            y += int(zh_size * 1.22)
        y += int(zh_size * .08)
    if en and f_en:
        d.text((80, y), en, font=f_en, fill=white)
        y += 84
    if not zh and not en:
        d.text((76, y), name, font=f_zh, fill=white)
        y += int(zh_size * 1.12)
    d.text((80, y + 10), content.get("tagline", ""), font=f_tag, fill=(255, 255, 255, 235))
    foot = []
    if lead.get("rating"):
        foot.append(f"Google {fmt_rating(lead['rating'])}（{lead.get('review_count', '')} 則評論）")
    addr = address_display(lead.get("address", ""))
    if addr:
        foot.append(addr)
    d.line([(80, 528), (W - 80, 528)], fill=(255, 255, 255, 70), width=1)
    d.text((80, 548), "　·　".join(foot), font=f_small, fill=(255, 255, 255, 210))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, "PNG", optimize=True)
    return True


def render_site(lead: dict, content: dict, cfg: dict, themes: dict, demo: bool, og_png: bool = False,
                fonts: list[dict] | None = None, site_dir: Path | None = None) -> str:
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
    mset = motifs.get(lead.get("theme") or "default") or motifs["default"]
    motif = mset["a"]
    # gallery 可以只寫檔名（放在 sites/<slug>/img/），也可以寫相對路徑或網址
    imgs = [g if ("/" in g or g.startswith("data:")) else f"img/{g}" for g in content.get("gallery", []) if g]
    labels = theme.get("gallery_labels") or ["店面", "服務區", "作品", "環境", "商品", "入口"]
    gallery_items = []
    if imgs:
        for i, src in enumerate(imgs):
            tall = photo_tall(src, site_dir)
            gallery_items.append({"img": src, "art": "", "tall": (i % 3 == 1) if tall is None else tall, "type": False,
                                  "label": labels[i % len(labels)]})
    else:
        # 沒有照片：標語直排一張、三張場景插畫（吧台、街角、窗邊；不加圖說，不假裝是照片），店名定了再畫
        gallery_items.append({"img": "", "art": "", "tall": True, "type": True, "label": ""})
        for key in ("counter", "street", "window"):
            gallery_items.append({"img": "", "art": key, "tall": key == "window", "type": False, "label": ""})
    mode = FONT_MODES.get(theme.get("mode", "bold"), FONT_MODES["bold"])
    fill = {"name": name, "city": lead.get("city", ""), "district": lead.get("district", "") or "在地"}
    statement = (content.get("statement") or theme.get("statement", "").format(**fill)).strip()
    statement_name = ""
    if not statement:
        statement, about = statement_from(about, content.get("tagline", ""))
        if statement.startswith(name):
            statement_name = name
            statement = statement[len(name):].lstrip()
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
    first_line = name_lines(name)[0] if name_lines(name) else {"kind": "en", "tokens": [name]}
    name_zh = "".join(first_line["tokens"]) if first_line["kind"] != "en" else name
    for g_ in gallery_items:
        if g_["art"] in ("counter", "street", "window"):
            g_["art"] = scene_tile(g_["art"], mset, name_zh, lead["slug"], lead.get("theme") or "default")
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
        "tagline": content.get("tagline", ""),
        "about_paragraphs": [about_opening(t_, name, city_district) if i_ == 0 else t_ for i_, t_ in enumerate(about)],
        "highlights": content.get("highlights", []), "services": services,
        "services_linked": any(s_["href"] for s_ in services),
        "og_image": (url.rstrip("/") + "/og.png") if og_png else "",
        "gallery_items": gallery_items,
        "weekday_hours": weekday_hours, "periods": periods, "today_hours": today_hours,
        "jsonld": jsonld, "favicon_svg": favicon_svg(theme["palette"]["pd"], initial),
        "type_ground": _mix(theme["palette"]["a_soft"], theme["palette"]["sf"], 0.55),
        "menu_title": {"cafe": "今日菜單", "breakfast": "今日菜單", "restaurant": "推薦菜色", "snack": "菜單", "hotpot": "菜單", "dessert": "今日甜點"}.get(lead.get("theme") or "", "服務與價目"),
        "ink2": _mix(theme["palette"]["a"], theme["palette"]["tx"], 0.55) if _lum(theme["palette"]["p"]) < 0.2 else theme["palette"]["p"],
        "name_len": name_len_units(name),
        "has_photos": bool(imgs),
        "gallery_name": "店內環境" if imgs else "店的樣子",
        "nav_labels": {"about": "關於我們", "services": content.get("nav_services") or theme.get("nav_services") or "服務項目",
                       "gallery": "店內環境" if imgs else "店的樣子", "info": "營業資訊"},
        "nav_services": content.get("nav_services") or theme.get("nav_services") or "服務項目",
        "order": [k for k in (content.get("order") or theme.get("order") or ["about", "services", "gallery", "info"])
                  if k in ("about", "services", "gallery", "info")],
        "feature_cta": feature_cta(content.get("feature_cta") or theme.get("feature_cta") or "詢問這一項", line_url),
        "gallery_title": (content.get("gallery_title") or (f"走進{name_zh}" if imgs
                          else theme.get("gallery_title", "{district}的一個角落").format(**fill))),
        "services_title": content.get("services_title") or theme.get("services_title") or "我們能為您做的",
        "signature": signature_block(theme, content, services),
        "hero_photo": imgs[0] if imgs else "",
        "about_photo": imgs[1] if len(imgs) > 1 else "",
        "name_zh": name_zh,
        "vcols": vertical_columns(alt_line(theme, content.get("tagline", ""), fill)),
        "vlen": max((len(c) for c in vertical_columns(content.get("tagline", ""))), default=6),
        "map_art": map_art(lead["slug"]),
        "address_disp": address_display(address),
        "closing_closed": closing_closed(lead.get("theme") or "default"),
        "scrim": _lum(theme["palette"]["p"]) > 0.2,
        "initial": initial, "name_tokens": name_tokens(name), "name_lines": name_lines(name), "address_short": address_short,
        "name_groups": [cjk_groups(ln["tokens"]) if ln["kind"] == "zh" else [[t] for t in ln["tokens"]] for ln in name_lines(name)],
        "services_lead": content.get("services_lead") or theme.get("services_lead") or "用實在的價格，認真做好每一件事。",
        "address_html": address_html(address, lead.get("city", ""), lead.get("district", "")),
        "mode": theme.get("mode", "bold"), "hero_layout": theme.get("hero", "side"),
        "fonts_url": mode["url"], "fonts": fonts or [], "font_display": mode["display"],
        "font_head": next((f["family"] for f in (fonts or []) if f.get("kind") == "head"), mode["head"]),
        "head_weight": mode["weight"],
        "statement_pre": pre, "statement_em": em, "statement_post": post, "statement_name": statement_name,
        # 兩段都短（一行放得下）就各自不拆，只在逗號換行；斷詞器不認得的詞（毛小孩）也不會被切開
        "statement_units": bool(pre) and len(pre) <= 11 and len(em) <= 11 and not post,
        "closing_title": closing_title(lead.get("theme") or "default", name),
        "year": date.today().year,
        "credit": brand["sender_name"] if show_credit else "",
        "credit_url": (brand.get("demo_base_url") or "") + "/",
        "sitecraft_name": brand["sender_name"], "sitecraft_contact_href": contact_href,
        "price_twd": brand.get("price_twd", 860),
    }
    tpl = _env.get_template("onepage.html.j2")
    from markupsafe import Markup
    # 橫幅：兩側是主圖騰與第三圖騰，中間是這一類的場景插畫（像一組靜物，不是三個圖示）
    key = lead.get("theme") or "default"
    hero_block = scene_markup(mset, key)
    band = (f'<g transform="translate(150 52) rotate(-8 100 100) scale(.7)">{drawable(motif)}</g>'
            f'<g transform="translate(300 0)">{hero_block}</g>'
            f'<g transform="translate(496 52) rotate(-5 100 100) scale(.7)">{drawable(mset.get("c", motif))}</g>')
    idle = mset.get("idle") or {"kind": "float", "shapes": [0]}

    band2 = hero_block
    closing_motif = motif if mset.get("hero") else mset.get("c", motif)
    closing_draw = idle_classes(drawable(closing_motif), mset.get("idle") or {"shapes": []}) if closing_motif is motif else drawable(closing_motif)
    return minify_css(tpl.render(b=b, t={**theme["palette"], "word": theme.get("word", "LOCAL"), "motif": Markup(motif),
                                         "motif_draw": Markup(drawable(motif)), "motif_idle": Markup(idle_classes(drawable(motif), idle)),
                                         "motif_scene": Markup(scene_markup(mset, key)),
                                         "motif_feature": Markup(print_scene(mset.get("hero") or motif, ground=False)),
                                         "motif_band2": Markup(band2), "motif_closing": Markup(closing_draw),
                                         "motif_b_draw": Markup(drawable(mset.get("b", motif))),
                                         "motif_about": Markup(scenes.storefront(mset, b["name_zh"], drawable, bg=False, key=key)),
                                         "motif_overlay": Markup(mset.get("b", motif)),
                                         "motif_b": Markup(mset.get("b", motif)), "motif_band": Markup(band)}, demo=demo))


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
              refresh_copy: bool = False, self_host_fonts: bool = True) -> Path:
    site_dir = SITES_DIR / lead["slug"]
    site_dir.mkdir(parents=True, exist_ok=True)
    theme = themes.get(lead.get("theme") or "default", themes["default"])
    content = load_or_make_content(lead, theme, site_dir, use_ai, refresh_copy)
    og_ok = og_image(lead, content, theme, site_dir / "og.png")
    html = render_site(lead, content, cfg, themes, demo=demo, og_png=og_ok, site_dir=site_dir)
    fonts = None
    if self_host_fonts:
        # 先算出這一頁用到的字，切出自架字型，再重畫一次
        fonts = fontkit.build_fonts(theme.get("mode", "bold"), html, site_dir)
        if fonts:
            html = render_site(lead, content, cfg, themes, demo=demo, og_png=og_ok, fonts=fonts, site_dir=site_dir)
    if not fonts:
        shutil.rmtree(site_dir / "fonts", ignore_errors=True)
        if self_host_fonts:
            print("  ! 無法切字型（缺 fonttools/brotli 或下載失敗），改用 Google Fonts 連結")
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
    ap.add_argument("--google-fonts", action="store_true", help="不自架字型，改用 Google Fonts 連結（離線或沒裝 fonttools 時）")
    args = ap.parse_args()

    load_env()
    cfg = load_config()
    themes = load_themes()
    b_ = cfg["brand"]
    if not b_.get("contact_email") and not str(b_.get("contact_line", "")).startswith("http"):
        print("! 提醒：config.json／.env 沒有填 CONTACT_EMAIL 或 CONTACT_LINE，示範網站底部的橫幅不會有「聯絡我們」按鈕，老闆看了沒辦法直接找你。")

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
        out = build_one(lead, cfg, themes, demo=demo, use_ai=args.ai_copy, refresh_copy=args.refresh_copy,
                        self_host_fonts=not args.google_fonts)
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
