"""自架字型：建站時依頁面實際用到的字，從開源變數字型切出小檔案（woff2）。

為什麼不用 Google Fonts 連結：中文字型在 Google Fonts 會被切成上百個 unicode-range 子集，
每個檔案抵達瀏覽器時整頁都要重排一次，手機上會吃掉幾百毫秒的主執行緒；而且首次載入的字型
樣貌取決於網路順序。這裡改成：
  1. 第一次把原始變數字型（SIL Open Font License）下載到 sitecraft/.fonts/（不進 git）。
  2. 每個站算出用到的字元集合，切出 2～4 個 woff2（中文約 100 KB、英文約 30 KB）。
  3. 檔案放在 sites/<slug>/fonts/，HTML 內用 @font-face 與 preload 載入，
     fontTools 不在時自動退回 Google Fonts 連結。
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE / ".fonts"
CACHE_DIR = FONT_DIR / "cache"
RAW = "https://raw.githubusercontent.com/google/fonts/main/"

# 原始檔：Google Fonts 的 GitHub 倉庫（OFL 授權，可商用、可再散布）
SOURCES = {
    "NotoSansTC[wght].ttf": RAW + "ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf",
    "NotoSerifTC[wght].ttf": RAW + "ofl/notoseriftc/NotoSerifTC%5Bwght%5D.ttf",
    "Fraunces[SOFT,WONK,opsz,wght].ttf": RAW + "ofl/fraunces/Fraunces%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf",
    "Fraunces-Italic[SOFT,WONK,opsz,wght].ttf": RAW + "ofl/fraunces/Fraunces-Italic%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf",
    "Syne[wght].ttf": RAW + "ofl/syne/Syne%5Bwght%5D.ttf",
    "SpaceGrotesk[wght].ttf": RAW + "ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
}

# 每種字型語氣要切哪些檔：family 是 @font-face 用的名稱（標題子集另取名字，
# 缺字時才會順著 font-family 清單退到同字重的內文字型，而不是退到系統字型）
#   kind: latin 只用拉丁字元集；head 只用標題用字、單一字重、先抓（首屏）；body 用整頁字元集、不先抓
#   wght: 保留的字重範圍（變數軸縮小，檔案跟著變小）；axes: 其他軸固定值
MODE_FILES = {
    "editorial": [
        {"family": "Fraunces", "src": "Fraunces[SOFT,WONK,opsz,wght].ttf", "out": "fraunces", "kind": "latin",
         "style": "normal", "wght": (400, 600), "axes": {"SOFT": 0, "WONK": 0}, "preload": True},
        {"family": "Fraunces", "src": "Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", "out": "fraunces-italic", "kind": "latin",
         "style": "italic", "wght": (400, 400), "axes": {"SOFT": 0, "WONK": 0}, "preload": True},
        {"family": "Noto Serif TC", "src": "NotoSerifTC[wght].ttf", "out": "noto-serif-tc-head", "kind": "head",
         "style": "normal", "wght": (600, 600), "axes": {}, "preload": True},
        {"family": "Noto Sans TC", "src": "NotoSansTC[wght].ttf", "out": "noto-sans-tc", "kind": "body",
         "style": "normal", "wght": (400, 700), "axes": {}, "preload": False},
    ],
    "bold": [
        {"family": "Syne", "src": "Syne[wght].ttf", "out": "syne", "kind": "latin",
         "style": "normal", "wght": (600, 800), "axes": {}, "preload": True},
        {"family": "Noto Sans TC Head", "src": "NotoSansTC[wght].ttf", "out": "noto-sans-tc-head", "kind": "head",
         "style": "normal", "wght": (800, 800), "axes": {}, "preload": True},
        {"family": "Noto Sans TC", "src": "NotoSansTC[wght].ttf", "out": "noto-sans-tc", "kind": "body",
         "style": "normal", "wght": (400, 700), "axes": {}, "preload": False},
    ],
    "mono": [
        {"family": "Space Grotesk", "src": "SpaceGrotesk[wght].ttf", "out": "space-grotesk", "kind": "latin",
         "style": "normal", "wght": (400, 600), "axes": {}, "preload": True},
        {"family": "Noto Sans TC Head", "src": "NotoSansTC[wght].ttf", "out": "noto-sans-tc-head", "kind": "head",
         "style": "normal", "wght": (600, 600), "axes": {}, "preload": True},
        {"family": "Noto Sans TC", "src": "NotoSansTC[wght].ttf", "out": "noto-sans-tc", "kind": "body",
         "style": "normal", "wght": (400, 700), "axes": {}, "preload": False},
    ],
}

# 用標題字型（--cjk-head）的元素：這些裡面的字進標題子集
HEAD_TAGS = {"h1", "h2", "h3"}
HEAD_CLASSES = {"display", "statement", "tagline", "vtext", "overlay"}

# 不管頁面有沒有出現都保留：JS 動態字串（營業狀態）、常用標點、數字
BASE_CHARS = set(
    "營業中休息今日公休明天開門已關閉打烊未提供時間至週一二三四五六日每天小時全年無"
    "「」『』，。、：；！？（）…—‧·–／％＄＃＆＊＋－＝＠～"
    "0123456789"
)
LATIN_BASE = set(chr(c) for c in range(0x20, 0x7F)) | set("ÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜßàáâãäåçèéêëìíîïñòóôõöøùúûüÿ’‘“”–—…·•×°©®™€£¥")

_available: bool | None = None


def available() -> bool:
    """fontTools + brotli 都在才能切字型。"""
    global _available
    if _available is None:
        try:
            import brotli  # noqa: F401
            import fontTools  # noqa: F401
            _available = True
        except ImportError:
            _available = False
    return _available


def ensure_sources(names: set[str], log=print) -> bool:
    """缺的原始字型檔就下載；任何一個失敗回 False（呼叫端退回 Google Fonts）。"""
    FONT_DIR.mkdir(exist_ok=True)
    for n in names:
        dst = FONT_DIR / n
        if dst.exists() and dst.stat().st_size > 100_000:
            continue
        try:
            import requests
            log(f"  [字型] 下載 {n} ...")
            with requests.get(SOURCES[n], stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = dst.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk)
                tmp.replace(dst)
        except Exception as e:  # noqa: BLE001
            log(f"  [字型] 下載失敗 {n}：{e}")
            return False
    return True


def charset_from_html(html: str) -> set[str]:
    """整份 HTML 的字元（含 JS 字串），去掉 <style> 區塊（只有 ASCII）。"""
    body = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    return {c for c in body if not c.isspace()} | BASE_CHARS


def head_charset_from_html(html: str) -> set[str]:
    """只收標題元素（h1/h2/h3、.statement、.tagline、.vtext、.overlay…）裡的字。"""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack: list[bool] = []
            self.chars: set[str] = set()
            self.skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("br", "wbr", "img", "meta", "link", "input", "hr", "path", "circle", "rect", "ellipse", "stop", "use"):
                return
            if tag in ("style", "script", "svg"):
                self.skip += 1
            classes = set((dict(attrs).get("class") or "").split())
            self.stack.append(tag in HEAD_TAGS or bool(classes & HEAD_CLASSES))

        def handle_endtag(self, tag):
            if tag in ("style", "script", "svg"):
                self.skip = max(0, self.skip - 1)
            if self.stack and tag not in ("br", "wbr", "img", "meta", "link", "input", "hr", "path", "circle", "rect", "ellipse", "stop", "use"):
                self.stack.pop()

        def handle_data(self, data):
            if not self.skip and any(self.stack):
                self.chars |= {c for c in data if not c.isspace()}

    p = P()
    p.feed(html)
    return p.chars | BASE_CHARS



def _subset(src: Path, out: Path, chars: set[str], wght: tuple[int, int], axes: dict) -> None:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    font = TTFont(str(src), lazy=False)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = [1, 2, 4, 6]
    opts.notdef_outline = True
    opts.hinting = False
    opts.desubroutinize = True
    s = subset.Subsetter(opts)
    s.populate(text="".join(sorted(chars)))
    s.subset(font)
    if "fvar" in font:
        limits = dict(axes)
        limits["wght"] = wght[0] if wght[0] == wght[1] else (wght[0], wght[1])
        names = {a.axisTag for a in font["fvar"].axes}
        limits = {k: v for k, v in limits.items() if k in names}
        font = instancer.instantiateVariableFont(font, limits, inplace=True, optimize=True, updateFontNames=False)
    font.flavor = "woff2"
    font.save(str(out))


def build_fonts(mode: str, html: str, site_dir: Path, log=print) -> list[dict] | None:
    """把這個站需要的字型切好放到 site_dir/fonts/。回傳 @font-face 要用的清單；做不到回 None。"""
    if not available():
        return None
    files = MODE_FILES.get(mode) or MODE_FILES["bold"]
    if not ensure_sources({f["src"] for f in files}, log):
        return None
    chars = charset_from_html(html)
    latin = {c for c in chars if ord(c) < 0x2E80} | LATIN_BASE
    head = head_charset_from_html(html) | set("0123456789")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_dir = site_dir / "fonts"
    out_dir.mkdir(exist_ok=True)
    for old in out_dir.glob("*.woff2"):
        old.unlink()
    result = []
    for f in files:
        use = {"latin": latin, "head": head, "body": chars}[f["kind"]]
        key = hashlib.sha1(("|".join([f["src"], str(f["wght"]), repr(sorted(f["axes"].items())), "".join(sorted(use))])).encode()).hexdigest()[:16]
        cached = CACHE_DIR / f"{f['out']}-{key}.woff2"
        if not cached.exists():
            try:
                _subset(FONT_DIR / f["src"], cached, use, f["wght"], f["axes"])
            except Exception as e:  # noqa: BLE001
                log(f"  [字型] 切割失敗 {f['src']}：{e}")
                return None
        name = f"{f['out']}-{key[:8]}.woff2"
        shutil.copyfile(cached, out_dir / name)
        lo, hi = f["wght"]
        result.append({"family": f["family"], "kind": f["kind"], "file": f"fonts/{name}", "style": f["style"],
                       "preload": f["preload"], "kb": (out_dir / name).stat().st_size // 1024,
                       "weight": str(lo) if lo == hi else f"{lo} {hi}"})
    return result
