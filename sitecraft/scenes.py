"""場景插畫：把每個類別的物件放進場景（店面、店裡、窗邊、街角），店面與店裡依類別換樣式。

沒有照片的店，插畫就是門面。單一圖示放大、旋轉看起來像版型；場景有前後、有環境，
同一套場景配上不同類別的物件，每一家看起來都是「自己的店」。店面招牌寫的是店名。

每個場景回傳 SVG 內容（不含 <svg>）：
  sc-bg 底色、sc-tone 偏移的色塊（雙色印刷感）、sc-paper 紙白（招牌、窗外天空）、
  sc-ln 線條群組（會在捲到時描出來），物件內的 fine / acc / acc2 沿用 motifs.json 的寫法。
顏色全部交給 CSS（含深色模式），這裡只管構圖。
"""
from __future__ import annotations

import html
import random

import svgbox

# drawable 由 build_site 傳入（避免循環 import）


def _place(m: str, cx: float, base: float, h: float, maxw: float | None = None) -> str:
    """把物件縮放到高度 h、底部貼齊 base、水平置中於 cx；線寬用 --k 補回來，縮小的物件線條不會變細。"""
    x, y, w, hh = svgbox.bbox(m)
    s = h / max(hh, 1)
    if maxw and w * s > maxw:
        s = maxw / max(w, 1)
    tx, ty = cx - (x + w / 2) * s, base - (y + hh) * s
    return f'<g transform="translate({tx:.1f} {ty:.1f}) scale({s:.3f})" style="--k:{1 / s:.2f}">{m}</g>'


def _sign_text(name: str, cx: float, cy: float, width: float, height: float = 30, parts: list[str] | None = None,
               size: float = 24) -> str:
    """招牌上的店名：放得下就一行；超過 8 個字且有詞組時，在最接近中間的詞界分兩行，字才不會小到看不清。"""
    lines = [name]
    if len(name) > 8 and parts and len(parts) > 1:
        best, at = None, 0
        for i in range(1, len(parts)):
            left = "".join(parts[:i])
            if best is None or abs(len(left) * 2 - len(name)) < best:
                best, at = abs(len(left) * 2 - len(name)), i
        lines = ["".join(parts[:at]), "".join(parts[at:])]
    longest = max(len(x) for x in lines)
    fs = min(size, width / (longest * 1.02), (height - 4) / (1.18 * len(lines)))
    if len(lines) == 1:
        return (f'<text class="sg" x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" '
                f'font-size="{fs:.1f}">{html.escape(name)}</text>')
    step = fs * 1.12
    return "".join(f'<text class="sg" x="{cx}" y="{cy + (i - .5) * step:.1f}" text-anchor="middle" dominant-baseline="central" '
                   f'font-size="{fs:.1f}">{html.escape(t)}</text>' for i, t in enumerate(lines))


STYLE_OF = {  # 店面樣式：依類別（餐飲遮陽棚、沙龍拱窗、服務業平雨遮、鍋物／餐館木造暖簾）
    "cafe": "awning", "breakfast": "awning", "dessert": "awning", "snack": "awning", "florist": "awning", "default": "awning",
    "hair": "arch", "beauty": "arch", "wellness": "arch", "lodging": "arch",
    "pet": "canopy", "clinic": "canopy", "education": "canopy", "gym": "canopy", "auto": "canopy",
    "hotpot": "noren", "restaurant": "noren",
}
ROOM_OF = {"hair": "salon", "beauty": "salon", "pet": "grooming", "hotpot": "dining", "restaurant": "dining"}


def _lamp(x: float, kind: str = "dome", drop: float = 0) -> str:
    """一盞吊燈（含燈罩的強調色）包成一組，CSS 讓它以吊線頂端為軸慢慢晃（休息時也在晃，頁面不會死掉）。"""
    if kind == "pendant":  # 吧台的大燈罩
        body = (f'<path class="fine" d="M{x} 0v46"/><path d="M{x - 22} 70c0-14 10-24 22-24s22 10 22 24z"/>'
                f'<path class="fine" d="M{x - 8} 76a8 5 0 0 0 16 0"/>')
    elif kind == "lantern":  # 鍋物的圓燈籠
        body = (f'<ellipse class="acc" cx="{x}" cy="58" rx="15" ry="18"/>'
                f'<path class="fine" d="M{x} 0v40"/><ellipse cx="{x}" cy="58" rx="15" ry="18"/>'
                f'<path class="fine" d="M{x - 15} 58h30M{x - 10} 44h20M{x - 10} 72h20"/>')
    else:  # 沙龍的小圓燈（drop：吊線再長一點）
        y = 40 + drop
        body = (f'<path class="acc" d="M{x - 12} {y}c0-8 5-12 12-12s12 4 12 12z"/>'
                f'<path class="fine" d="M{x} 0v{30 + drop}"/><path d="M{x - 12} {y}c0-8 5-12 12-12s12 4 12 12z"/>')
    return f'<g class="sway">{body}</g>'


def _plate(x: float, y: float) -> str:
    """門上的小牌子：頁面判斷營業中／休息中後由 JS 寫字（沒有 JS 就不顯示）。"""
    return (f'<g class="plate"><path d="M{x + 12} {y}l10-8 10 8"/><rect x="{x}" y="{y}" width="44" height="18" rx="3"/>'
            f'<text x="{x + 22}" y="{y + 9.5}" text-anchor="middle" dominant-baseline="central" font-size="10"></text></g>')


def _front_awning(a: str, c: str) -> dict:
    stripes = "".join(
        f'<path class="acc" d="M{92 + 27 * i} 126h27l{(76 + 31 * (i + 1)) - (92 + 27 * (i + 1))} 24h-31z"/>'
        for i in range(0, 8, 2))
    scallops = "M76 150" + "a15.5 10 0 0 0 31 0" * 8
    return {
        "lines": ('<path d="M70 266V70h260v196"/><path d="M62 62h276v8H62z"/>'
                  '<rect x="104" y="80" width="192" height="36" rx="4"/>'
                  '<path d="M92 126h216l16 24H76z"/>' + f'<path class="fine" d="{scallops}"/>'
                  '<rect x="94" y="168" width="136" height="82" rx="2"/><path d="M88 250h148"/>'
                  '<path class="fine" d="M104 184l14-10M106 198l26-18"/>' + _place(a, 162, 242, 58, 96)
                  + '<rect x="246" y="164" width="60" height="102" rx="2"/><path class="fine" d="M256 232v-38a20 20 0 0 1 40 0v38z"/>'
                  '<circle class="acc" cx="297" cy="240" r="3.2"/><path class="fine" d="M240 266v-4h72v4"/>'
                  '<path class="fine" d="M330 132h26M350 132v2"/><circle cx="350" cy="152" r="17"/>' + _place(c, 350, 162, 18, 24)
                  + '<path d="M26 266l4-24h32l4 24z"/><path class="fine" d="M46 242c-2-22-14-34-26-38M46 242c2-24 12-38 26-44M46 242c-8-14-6-28 2-38"/>'),
        "under": stripes,
        "tone": '<rect x="70" y="70" width="260" height="196"/><path d="M26 266l4-24h32l4 24z"/><circle cx="350" cy="152" r="17"/>',
        "paper": '<rect x="104" y="80" width="192" height="36" rx="4"/>',
        "windows": '<rect x="94" y="168" width="136" height="82" rx="2"/>',
        "sign": (200, 99, 172, 34), "plate": (254, 176),
    }


def _front_arch(a: str, c: str) -> dict:
    win = "M92 250V174a34 34 0 0 1 68 0v76z", "M240 250V174a34 34 0 0 1 68 0v76z"
    leaves = "".join(f'<path class="fine" d="M{x} 250c-2-8-8-12-14-12M{x} 250c2-10 8-14 14-14"/>' for x in (108, 140, 256, 288))
    return {
        "lines": ('<path d="M70 266V70h260v196"/><path d="M62 70h276"/><path class="fine" d="M66 62h268v8"/>'
                  '<rect x="100" y="82" width="200" height="32" rx="16"/>'
                  f'<path d="{win[0]}"/><path d="{win[1]}"/><path class="fine" d="M126 140v110M274 140v110"/>'
                  + _place(a, 126, 238, 46, 56) + _place(c, 274, 238, 40, 56)
                  + '<path d="M86 250h80v12H86zM234 250h80v12h-80z"/>' + leaves
                  + '<path d="M176 266V180a24 24 0 0 1 48 0v86"/><path class="fine" d="M186 266V184a14 14 0 0 1 28 0v82"/>'
                  '<circle class="acc" cx="214" cy="226" r="3"/>'
                  '<path class="fine" d="M168 152v-10M232 152v-10"/><circle class="acc" cx="168" cy="158" r="5"/><circle class="acc" cx="232" cy="158" r="5"/>'
                  '<path class="fine" d="M330 120h24"/><circle cx="350" cy="138" r="15"/>' + _place(c, 350, 147, 16, 20)),
        "under": "",
        "tone": f'<rect x="70" y="70" width="260" height="196"/><path d="{win[0]}"/><path d="{win[1]}"/>',
        "paper": '<rect x="100" y="82" width="200" height="32" rx="16"/>',
        "windows": f'<path d="{win[0]}"/><path d="{win[1]}"/>',
        "sign": (200, 98, 180, 30), "plate": (178, 196),
    }


def _front_canopy(a: str, c: str) -> dict:
    return {
        "lines": ('<path d="M70 266V70h260v196"/><path d="M62 62h276v8H62z"/>'
                  '<rect x="86" y="80" width="228" height="38" rx="6"/>'
                  '<path d="M78 128h244v8H78z"/><path class="fine" d="M92 136l10 10M308 136l-10 10"/>'
                  '<rect x="86" y="152" width="150" height="98" rx="4"/><path class="fine" d="M161 152v98M96 166l14-10"/>'
                  + _place(a, 124, 238, 44, 56) + _place(c, 199, 238, 40, 60)
                  + '<path d="M80 250h162"/>'
                  '<rect x="250" y="152" width="58" height="114" rx="3"/><rect class="fine" x="258" y="162" width="42" height="64" rx="2"/>'
                  '<circle class="acc" cx="300" cy="240" r="3"/>'
                  '<path d="M316 266c0-7 5-10 12-10s12 3 12 10z"/>'
                  '<path d="M26 266l4-24h32l4 24z"/><path class="fine" d="M46 242c-2-22-14-34-26-38M46 242c2-24 12-38 26-44M46 242c-8-14-6-28 2-38"/>'),
        "under": '<path class="acc" d="M78 128h244v8H78z"/>',
        "tone": '<rect x="70" y="70" width="260" height="196"/><path d="M26 266l4-24h32l4 24z"/>',
        "paper": '<rect x="86" y="80" width="228" height="38" rx="6"/>',
        "windows": '<rect x="86" y="152" width="150" height="98" rx="4"/>',
        "sign": (200, 99, 212, 36), "plate": (257, 192),
    }


def _front_noren(a: str, c: str) -> dict:
    slats = "".join(f"M{x} 96v170" for x in (78, 86, 314, 322))
    panels = "".join(f'<path class="acc" d="M{152 + 25 * i} 140h23v50h-23z"/>' for i in range(4))
    lantern = lambda x: (f'<path class="fine" d="M{x} 84v10"/><ellipse cx="{x}" cy="110" rx="11" ry="15"/>'  # noqa: E731
                         f'<path class="fine" d="M{x - 11} 110h22M{x - 7} 98h14M{x - 7} 122h14"/>')
    return {
        "lines": ('<path d="M70 266V96h260v170"/><path d="M52 96l18-22h260l18 22z"/><path class="fine" d="M84 84h232"/>'
                  f'<path class="fine" d="{slats}"/>'
                  '<rect x="110" y="100" width="180" height="30" rx="3"/>'
                  + lantern(96) + lantern(304)
                  + '<path d="M146 138h108"/><rect x="150" y="138" width="100" height="128"/><path class="fine" d="M200 192v74"/>'
                  + _place(a, 200, 186, 26, 40)
                  + '<rect x="96" y="160" width="40" height="64"/><path class="fine" d="M116 160v64M96 182h40M96 204h40"/>'
                  '<rect x="264" y="160" width="40" height="64"/><path class="fine" d="M284 160v64M264 182h40M264 204h40"/>'
                  + _place(c, 284, 220, 16, 24)
                  + '<path d="M338 266l8-44h22l8 44"/><path class="fine" d="M346 236h28M348 246h24"/>'),
        "under": panels + '<path class="acc2" d="M52 96l18-22h260l18 22z"/>'
                 '<ellipse class="acc" cx="96" cy="110" rx="11" ry="15"/><ellipse class="acc" cx="304" cy="110" rx="11" ry="15"/>',
        "tone": '<rect x="70" y="96" width="260" height="170"/>',
        "paper": '<rect x="110" y="100" width="180" height="30" rx="3"/>',
        "windows": '<rect x="96" y="160" width="40" height="64"/><rect x="264" y="160" width="40" height="64"/>',
        "sign": (200, 115, 172, 28), "plate": (178, 214),
    }


FRONTS = {"awning": _front_awning, "arch": _front_arch, "canopy": _front_canopy, "noren": _front_noren}


def storefront(mset: dict, name: str, drawable, ground: bool = True, bg: bool = True, key: str = "default",
               parts: list[str] | None = None) -> str:
    """店面：招牌寫店名、櫥窗上貼著這個類別的主圖騰、門上掛營業牌；外觀依類別換（遮陽棚、拱窗、平雨遮、暖簾）。"""
    a, c = mset["a"], mset.get("c", mset["a"])
    f = FRONTS[STYLE_OF.get(key, "awning")](a, c)
    ground_lines = '<path d="M0 266H400"/><path class="fine" d="M16 280h56M104 280h28M268 280h48M344 280h40"/>' if ground else ""
    tone = f'<g class="sc-tone" transform="translate(7 7)">{f["tone"]}</g>'
    paper = (f'<g class="sc-paper">{f["paper"]}</g><g class="sc-paper win">{f["windows"]}</g>'
             f'<g class="glow">{f["windows"]}</g>')
    sx, sy, sw, sh = f["sign"]
    return ((('<rect class="sc-bg" width="400" height="300"/><circle class="acc2" cx="356" cy="40" r="22"/>') if bg else "")
            + tone + paper + f["under"] + f'<g class="sc-ln">{drawable(ground_lines + f["lines"])}</g>'
            + _sign_text(name, sx, sy, sw, sh, parts) + _plate(*f["plate"]))


def detail(mset: dict, drawable, key: str = "default", uid: str = "w") -> str:
    """直式的近景：髮廊洗頭區、寵物吹整台、鍋物醬料台；其他類別是窗邊。"""
    room = ROOM_OF.get(key, "")
    if room == "salon":
        return wash(mset, drawable)
    if room == "grooming":
        return drying(mset, drawable)
    if room == "dining":
        return sauce_bar(mset, drawable)
    return window(mset, drawable, uid)


def wash(mset: dict, drawable) -> str:
    """洗頭區：躺椅靠向洗頭槽，上方層架放瓶罐，旁邊一疊毛巾，天花板垂一盆植物。"""
    c = mset.get("c", mset["a"])
    lines = (
        '<path d="M0 360H300"/><path class="fine" d="M0 180H300"/>'
        '<path d="M150 214h110v8a42 42 0 0 1-42 42h-26a42 42 0 0 1-42-42z"/><path d="M146 214h118"/>'
        '<path d="M236 214v-28h-22v8"/><path d="M190 264v96h28v-96"/>'
        '<path d="M28 296h124a8 8 0 0 1 0 16H28a8 8 0 0 1 0-16z"/><path d="M140 296l34-58a8 8 0 0 1 14 8l-30 50"/>'
        '<path d="M52 312v48M128 312v48M40 360h100"/>'
        '<path d="M24 120h126"/><path class="fine" d="M34 120l6 8M140 120l-6 8"/>'
        '<path d="M38 120v-24h12v24M41 96v-6h6"/><path d="M60 120v-30h12v30M63 90v-6h6"/>' + _place(c, 116, 120, 26, 36)
        + '<path d="M196 150h86"/><rect x="206" y="128" width="64" height="11" rx="5"/><rect x="210" y="139" width="60" height="11" rx="5"/>'
        '<path class="fine" d="M248 0v36"/><path d="M234 36h28l-4 18h-20z"/>'
        '<path class="fine" d="M248 54c-10 20-24 28-36 30M248 54c8 22 22 32 34 34M248 54c0 20-4 34-10 44"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><path d="M150 214h110v8a42 42 0 0 1-42 42h-26a42 42 0 0 1-42-42z"/>'
            '<path d="M28 296h124a8 8 0 0 1 0 16H28a8 8 0 0 1 0-16z"/></g>')
    return ('<rect class="sc-bg" width="300" height="400"/>' + tone
            + '<path class="acc2" d="M140 296l34-58a8 8 0 0 1 14 8l-30 50z"/><rect class="acc" x="206" y="128" width="64" height="11" rx="5"/>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')


def drying(mset: dict, drawable) -> str:
    """寵物吹整台：桌上一條毛巾、梳子與刷子，旁邊立式吹風機，牆上掛一幅小框。"""
    a, c = mset["a"], mset.get("c", mset["a"])
    lines = (
        '<path d="M0 360H300"/><path class="fine" d="M0 180H300"/>'
        '<path d="M22 262h196v10H22z"/><path d="M40 272v88M200 272v88"/><path class="fine" d="M40 330h160"/>'
        '<path d="M56 262v-14h80v14"/><path class="fine" d="M66 248v14M76 248v14M118 248v14"/>'
        '<path d="M150 262v-6h44v6"/><path class="fine" d="M154 256v-6M162 256v-6M170 256v-6M178 256v-6M186 256v-6"/>'
        + _place(c, 110, 248, 24, 40)
        + '<path d="M254 360V150"/><path d="M232 360h44"/>'
        '<path d="M212 128h44a12 12 0 0 1 12 12v8a12 12 0 0 1-12 12h-44z"/><path d="M212 132v24"/>'
        '<path class="fine" d="M200 140l-14-6M200 148h-16M200 156l-14 6"/>'
        '<path class="fine" d="M268 150c18 30 16 80 0 120"/>'
        '<rect x="36" y="70" width="70" height="60" rx="3"/>' + _place(a, 71, 120, 36, 50)
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><path d="M22 262h196v10H22z"/><rect x="36" y="70" width="70" height="60"/>'
            '<path d="M212 128h44a12 12 0 0 1 12 12v8a12 12 0 0 1-12 12h-44z"/></g>')
    return ('<rect class="sc-bg" width="300" height="400"/>' + tone
            + '<rect class="sc-paper" x="36" y="70" width="70" height="60" rx="3"/>'
            + '<path class="acc" d="M56 262v-14h80v14z"/><path class="acc2" d="M212 128h44a12 12 0 0 1 12 12v8a12 12 0 0 1-12 12h-44z"/>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')


def sauce_bar(mset: dict, drawable) -> str:
    """醬料台：檯面上一排醬料碗，橫桿上掛湯勺，層架擺罐子，旁邊一塊木菜牌。"""
    c = mset.get("c", mset["a"])
    bowls = "".join(f'<path d="M{x - 15} 250h30c0 8-7 13-15 13s-15-5-15-13z"/>' for x in (46, 86, 126, 166, 206))
    sauces = "".join(f'<ellipse class="{cl}" cx="{x}" cy="252" rx="11" ry="3"/>'
                     for x, cl in ((46, "acc"), (86, "acc2"), (126, "acc"), (166, "acc2"), (206, "acc")))
    ladles = "".join(f'<path d="M{x} 150v36"/><path d="M{x - 9} 186h18c0 6-4 10-9 10s-9-4-9-10z"/>' for x in (60, 100, 140))
    lines = (
        '<path d="M0 360H300"/><path class="fine" d="M0 180H300"/>'
        '<path d="M14 263h272v10H14z"/><path d="M26 273v87h248v-87"/><path class="fine" d="M80 278v76M140 278v76M200 278v76"/>'
        + bowls + '<path d="M30 150h150"/>' + ladles
        + '<path d="M196 110h90"/><path class="fine" d="M206 110l6 8M276 110l-6 8"/>'
        '<path d="M206 110V88a4 4 0 0 1 4-4h14a4 4 0 0 1 4 4v22"/><path d="M238 110V92h18v18"/><path d="M262 110V84h16v26"/>'
        '<rect x="228" y="150" width="30" height="92" rx="3"/><path class="fine" d="M243 160v18M243 186v12M243 206v22"/>'
        + _place(c, 250, 263, 18, 34)
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><path d="M14 263h272v10H14z"/><rect x="228" y="150" width="30" height="92"/></g>')
    return ('<rect class="sc-bg" width="300" height="400"/>' + tone + sauces
            + '<rect class="sc-paper" x="228" y="150" width="30" height="92" rx="3"/>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')


def interior(mset: dict, drawable, key: str = "default", wide: bool = False) -> str:
    """店裡：依類別換場景（吧台、髮廊鏡台、寵物美容台、鍋物餐桌）。

    wide=True 給橫幅首屏用：同一個房間（400x300）放在中間，左右各接 100 寬的一段（600x300），
    舞台比較寬，標題下方不會只有一小塊插畫。"""
    room = ROOM_OF.get(key, "")
    core = {"salon": salon, "grooming": grooming, "dining": dining}.get(room, counter)(mset, drawable)
    if not wide:
        return core
    core = core.replace('<rect class="sc-bg" width="400" height="300"/>', "")
    left, right, tone, fills = _WINGS.get(room, _WINGS[""])
    horizon = {"salon": 252, "grooming": 150, "dining": 150}.get(room)
    lines = ('<path d="M0 266H100M500 266H600"/>'
             + (f'<path class="fine" d="M0 {horizon}H100M500 {horizon}H600"/>' if horizon else "") + left + right)
    return (f'<g class="sc-tone" transform="translate(7 7)">{tone}</g>' + fills
            + f'<g transform="translate(100 0)">{core}</g>' + f'<g class="sc-ln">{drawable(lines)}</g>')


# 橫幅舞台兩側（左翼 x 0–100、右翼 x 500–600，地板 y=266）：(左線條, 右線條, 偏移色塊, 強調色填色)
_WINGS = {
    "salon": (  # 左：接待櫃台、花瓶與吊燈；右：牆上層架的瓶罐，地上一籃毛巾
        _lamp(50, drop=24) +
        '<path d="M10 206h84"/><path d="M16 206v60M88 206v60"/><path class="fine" d="M16 226h72"/>'
        '<path d="M28 206l-2-14h12l-2 14"/><path class="fine" d="M32 192c-2-10-8-16-14-18M32 192c2-12 8-18 16-20M32 192c0-10 2-18 6-22"/>'
        '<path d="M60 206v-8a8 8 0 0 1 16 0v8"/><path class="fine" d="M68 190v-4"/>',
        _lamp(550, drop=24) +
        '<path d="M512 118h80"/><path class="fine" d="M522 118l6 8M582 118l-6 8"/>'
        '<path d="M524 118v-22h9v22M526 96v-5h5"/><path d="M542 118v-28h10v28M544 90v-5h6"/><path d="M562 118v-18h12v18"/>'
        '<path d="M520 266l6-34h56l6 34"/><path class="fine" d="M524 244h60"/>'
        '<rect x="528" y="220" width="52" height="10" rx="5"/><rect x="534" y="210" width="40" height="10" rx="5"/>',
        '<path d="M10 206h84v60H10z"/><path d="M520 266l6-34h56l6 34z"/>',
        '<rect class="acc2" x="528" y="220" width="52" height="10" rx="5"/>'),
    "dining": (  # 左：通往廚房的門，掛著暖簾；右：飲料冰櫃
        '<path d="M14 266V92h76v174"/><path d="M14 92h76v52H14"/><path class="fine" d="M39 92v52M65 92v52"/>'
        '<path class="fine" d="M30 170c-4-8 4-12 0-20M52 166c-4-8 4-12 0-20M74 170c-4-8 4-12 0-20"/>',
        '<rect x="516" y="132" width="66" height="134" rx="4"/><rect class="fine" x="524" y="140" width="50" height="96" rx="2"/>'
        '<path class="fine" d="M524 172h50M524 204h50"/>'
        '<path class="fine" d="M532 172v-16h6v16M546 172v-20h6v20M560 172v-14h6v14M532 204v-18h6v18M546 204v-14h6v14M560 204v-18h6v18"/>'
        '<path d="M524 248h50"/>',
        '<path d="M14 92h76v52H14z"/><rect x="516" y="132" width="66" height="134"/>',
        '<path class="acc2" d="M14 92h76v52H14z"/>'),
    "": (  # 左：一盆高高的龜背芋與小凳；右：立在地上的黑板菜單
        '<path d="M22 266l4-34h36l4 34"/><path class="fine" d="M44 232c-2-30-14-50-30-60M44 232c0-34 6-58 22-74M44 232c4-26 18-40 36-44"/>'
        '<path class="fine" d="M14 172c8-4 14 0 16 6M66 158c4-8 12-8 16-2M80 188c4-6 12-4 12 2"/>',
        '<path d="M516 266l12-110h48l12 110"/><rect x="522" y="168" width="60" height="62" rx="3"/>'
        '<path class="fine" d="M532 184h40M532 196h28M532 208h34M532 220h22"/><path class="fine" d="M528 248h48"/>',
        '<path d="M22 266l4-34h36l4 34z"/><rect x="522" y="168" width="60" height="62"/>',
        '<rect class="acc2" x="522" y="168" width="60" height="62" rx="3"/>'),
}


def counter(mset: dict, drawable) -> str:
    """吧台／工作檯：兩盞吊燈、牆上的畫框與層架，檯面上是這個類別的工具與小物。"""
    b, c = mset.get("b", mset["a"]), mset.get("c", mset["a"])
    lines = (
        _lamp(110, "pendant") + _lamp(290, "pendant") +
        '<rect x="26" y="92" width="56" height="68" rx="2"/><rect class="fine" x="33" y="99" width="42" height="54"/>'
        + _place(c, 54, 146, 30, 32)
        + '<path d="M232 122h140"/><path class="fine" d="M246 122l8 10M358 122l-8 10"/>'
        '<path d="M244 122v-22a4 4 0 0 1 4-4h12a4 4 0 0 1 4 4v22"/><path class="fine" d="M246 90h16"/>'
        '<path d="M272 122v-16h14v16"/><path class="fine" d="M300 122V94M308 122V98M316 122V92"/><path d="M326 122l7-26"/>'
        '<path d="M344 122l-2-12h18l-2 12z"/><path class="fine" d="M351 110c-2-8-8-12-12-12M351 110c2-10 8-14 14-14"/>'
        '<path d="M14 196h372"/><path d="M28 202v64h344v-64"/><path class="fine" d="M14 196v6h372v-6"/>'
        '<path class="fine" d="M90 208v52M150 208v52M210 208v52M270 208v52M330 208v52"/><path d="M0 266H400"/>'
        + _place(b, 156, 196, 92, 116) + _place(c, 316, 196, 34, 60)
        + '<path d="M238 196v-16h12v16z"/><path class="fine" d="M244 180c0-12 4-20 10-26M245 172c6-2 10-6 12-12"/>'
        '<circle class="acc" cx="255" cy="152" r="6"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><rect x="28" y="196" width="344" height="70"/>'
            '<path d="M88 70c0-14 10-24 22-24s22 10 22 24zM268 70c0-14 10-24 22-24s22 10 22 24z"/>'
            '<rect x="26" y="92" width="56" height="68"/></g>')
    glow = '<g class="acc2"><path d="M70 76h80l26 110H44z" opacity=".35"/><path d="M250 76h80l26 110H224z" opacity=".35"/></g>'
    return ('<rect class="sc-bg" width="400" height="300"/>' + glow + tone
            + '<rect class="sc-paper" x="33" y="99" width="42" height="54"/>' + f'<g class="sc-ln">{drawable(lines)}</g>')


def salon(mset: dict, drawable) -> str:
    """髮廊／美容：兩面拱形鏡子與檯面，鏡前一張油壓椅，右邊推車放工具，角落一盆高植物。"""
    b, c = mset.get("b", mset["a"]), mset.get("c", mset["a"])
    mirror = lambda x: (f'<path d="M{x} 150V96a34 34 0 0 1 68 0v54z"/>'  # noqa: E731
                        f'<path class="fine" d="M{x + 14} 80c8-8 20-10 30-6M{x + 10} 132l16-16"/>')
    lines = (
        '<path d="M0 266H400"/><path class="fine" d="M0 252H400"/>'
        + _lamp(104) + _lamp(264)
        + mirror(70) + mirror(230)
        + '<path d="M56 150h296v8H56z"/>' + _place(c, 180, 150, 24, 40)
        + '<path d="M246 150v-14h7v14M248 136v-4h3"/><path d="M322 150v-16h9v16M324 134v-4h5"/>'
        '<path d="M84 214V184a12 12 0 0 1 12-12h16a12 12 0 0 1 12 12v30"/>'
        '<path d="M78 214h52a5 5 0 0 1 0 10H78a5 5 0 0 1 0-10z"/><path d="M104 224v20M104 244l-18 22M104 244l18 22"/>'
        '<path d="M286 266v-70h48v70"/><path d="M286 196h48M286 230h48"/>'
        '<circle class="fine" cx="292" cy="268" r="3"/><circle class="fine" cx="328" cy="268" r="3"/>'
        + _place(b, 310, 196, 34, 44)
        + '<path d="M18 266l4-28h28l4 28z"/><path class="fine" d="M36 238c-4-30-18-44-30-50M36 238c2-34 14-52 30-60M36 238c-10-16-10-36-2-50"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><path d="M56 150h296v8H56z"/><path d="M70 150V96a34 34 0 0 1 68 0v54z"/>'
            '<path d="M230 150V96a34 34 0 0 1 68 0v54z"/><path d="M286 196h48v70h-48z"/></g>')
    glass = '<g class="sc-paper"><path d="M70 150V96a34 34 0 0 1 68 0v54z"/><path d="M230 150V96a34 34 0 0 1 68 0v54z"/></g>'
    # 鏡面上的一道反光：首屏時跟著捲動滑過兩面鏡子（--hp），其他地方就停在原位
    glint = ('<clipPath id="mirrorGlass"><path d="M70 150V96a34 34 0 0 1 68 0v54z"/><path d="M230 150V96a34 34 0 0 1 68 0v54z"/></clipPath>'
             '<g clip-path="url(#mirrorGlass)"><g class="glint"><path d="M48 160L104 56h16L64 160z"/><path d="M208 160L264 56h16L224 160z"/></g></g>')
    return ('<rect class="sc-bg" width="400" height="300"/>' + tone + glass + glint
            + '<path class="acc2" d="M78 214h52a5 5 0 0 1 0 10H78a5 5 0 0 1 0-10z"/>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')


def grooming(mset: dict, drawable) -> str:
    """寵物美容室：左邊美容台（含吊桿），右邊有蓮蓬頭的洗澡缸，牆上掛牽繩，架上疊毛巾。"""
    a, b, c = mset["a"], mset.get("b", mset["a"]), mset.get("c", mset["a"])
    tiles = "".join(f"M{x} 150v116" for x in range(40, 400, 40))
    lines = (
        '<path d="M0 266H400"/><path class="fine" d="M0 150H400"/>' + f'<path class="fine" d="{tiles}" opacity=".5"/>'
        '<rect x="38" y="58" width="56" height="50" rx="3"/>' + _place(a, 66, 100, 30, 40)
        + '<path d="M36 186h124v8H36z"/><path d="M54 194v72M142 194v72"/><path class="fine" d="M54 238h88"/>'
        '<path d="M152 186V118h-34"/><path class="fine" d="M120 118v16a8 8 0 0 0 16 0v-16"/>'
        + _place(b, 84, 186, 16, 40)
        + '<path d="M182 100h48"/><path class="fine" d="M192 100v8a4 4 0 0 0 8 0M214 100v8a4 4 0 0 0 8 0"/>'
        '<path class="fine" d="M196 112c-8 24 8 40 0 60M218 112c-6 18 6 30 0 46"/>'
        '<path d="M222 196h140v20a26 26 0 0 1-26 26h-88a26 26 0 0 1-26-26z"/><path d="M216 196h152"/>'
        '<path d="M240 242l-6 24M344 242l6 24"/>'
        '<path d="M346 196V118h-28"/><path d="M302 114h22v8h-22z"/><path class="fine" d="M306 132v8M314 132v10M310 146v6M320 134v6"/>'
        '<path d="M262 92h96"/><path class="fine" d="M272 92l6 8M348 92l-6 8"/>'
        '<rect x="300" y="72" width="40" height="9" rx="4"/><rect x="304" y="81" width="36" height="9" rx="4"/>'
        + _place(c, 280, 92, 22, 30)
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><path d="M36 186h124v8H36z"/>'
            '<path d="M222 196h140v20a26 26 0 0 1-26 26h-88a26 26 0 0 1-26-26z"/><rect x="38" y="58" width="56" height="50"/></g>')
    return ('<rect class="sc-bg" width="400" height="300"/>' + tone
            + '<rect class="sc-paper" x="38" y="58" width="56" height="50" rx="3"/>'
            + '<path class="acc2" d="M222 196h140v20a26 26 0 0 1-26 26h-88a26 26 0 0 1-26-26z"/>'
            + '<rect class="acc" x="300" y="72" width="40" height="9" rx="4"/>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')


def dining(mset: dict, drawable) -> str:
    """鍋物／餐館：三顆圓燈籠、牆上一排木製菜牌，桌上一鍋正在煮，兩張圓凳。"""
    b, c = mset.get("b", mset["a"]), mset.get("c", mset["a"])
    lantern = lambda x: (f'<path class="fine" d="M{x} 0v40"/><ellipse cx="{x}" cy="58" rx="15" ry="18"/>'  # noqa: E731
                         f'<path class="fine" d="M{x - 15} 58h30M{x - 10} 44h20M{x - 10} 72h20"/>')
    tags = "".join(f'<rect x="{x}" y="70" width="14" height="58" rx="2"/><path class="fine" d="M{x + 7} 78v12M{x + 7} 96v8M{x + 7} 110v10"/>'
                   for x in (300, 320, 340, 360))
    lines = (
        '<path d="M0 266H400"/><path class="fine" d="M0 150H400"/>'
        + _lamp(110, "lantern") + _lamp(200, "lantern") + _lamp(290, "lantern") + tags
        + '<path d="M96 196h208"/><path class="fine" d="M96 196v6h208v-6"/><path d="M118 202v64M282 202v64"/>'
        + _place(b, 200, 196, 58, 90) + _place(c, 272, 196, 22, 36)
        + '<path class="fine" d="M104 192a16 4 0 0 0 32 0M106 186l22-8M288 192a8 3 0 0 0 0-1"/><path d="M140 196v-9h11v9zM250 196v-9h11v9z"/>'
        '<path d="M44 222h44M50 222l-4 44M82 222l4 44"/><path class="fine" d="M48 246h36"/>'
        '<path d="M312 222h44M318 222l-4 44M350 222l4 44"/><path class="fine" d="M316 246h36"/>'
        '<rect x="22" y="70" width="70" height="52" rx="3"/><path class="fine" d="M32 84h50M32 96h36M32 108h44"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><path d="M96 196h208v6H96z"/><rect x="22" y="70" width="70" height="52"/>'
            '<path d="M300 70h74v58h-74z"/></g>')
    return ('<rect class="sc-bg" width="400" height="300"/>' + tone
            + '<rect class="sc-paper" x="22" y="70" width="70" height="52" rx="3"/>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')


def window(mset: dict, drawable, uid: str = "w") -> str:
    """窗邊（直式）：拱窗外是屋頂與山，窗台上一盆植物和這個類別的小物，旁邊垂著窗簾。"""
    c = mset.get("c", mset["a"])
    clip = f"wcl{uid}"
    outside = ('<path class="fine" d="M64 290c26-18 54-22 84-10s58 10 88-6"/>'
               '<path class="fine" d="M64 322h18l14-14 14 14h26v-18h22v18h20l12-12 12 12h40"/>')
    view = (f'<g clip-path="url(#{clip})"><rect class="sc-paper" x="60" y="60" width="180" height="280"/>'
            '<circle class="acc" cx="194" cy="134" r="24"/>'
            '<path class="sc-tone" d="M64 290c26-18 54-22 84-10s58 10 88-6v66H64z"/>'
            f'<g class="sc-ln">{drawable(outside)}</g></g>')
    lines = (
        '<path d="M64 336V156a86 86 0 0 1 172 0v180"/><path class="fine" d="M74 336V158a76 76 0 0 1 152 0v178"/>'
        '<path class="fine" d="M150 72v264M74 220h152"/>'
        '<path d="M16 36h268"/><circle class="fine" cx="36" cy="36" r="4"/><circle class="fine" cx="52" cy="36" r="4"/><circle class="fine" cx="68" cy="36" r="4"/>'
        '<path class="fine" d="M30 40c4 100-10 200 4 300M70 40c-6 96 8 200-8 300M50 40c2 100-6 200 0 300"/>'
        '<path d="M36 336h228"/><path class="fine" d="M44 348h212M44 336v12M256 336v12"/>'
        '<path d="M200 336l-5-30h46l-5 30z"/><path class="fine" d="M218 306c-10-32-30-42-46-44M218 306c2-36 18-52 36-58M218 306c-16-20-12-46 4-60"/>'
        + _place(c, 118, 336, 56, 84)
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><path d="M30 40h40c-6 96 8 200-8 300H34c10-100-6-204-4-300z"/>'
            '<path d="M200 336l-5-30h46l-5 30z"/></g>')
    return (f'<defs><clipPath id="{clip}"><path d="M64 336V156a86 86 0 0 1 172 0v180z"/></clipPath></defs>'
            '<rect class="sc-bg" width="300" height="400"/>' + view + tone
            + '<path class="acc2" d="M30 40h40c-6 96 8 200-8 300H34c10-100-6-204-4-300z"/>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')


def _vsign(text: str, cx: float, top: float, height: float, size: float = 15) -> str:
    """直式招牌的字：一字一行，字級依字數縮放（最多 6 個字）。"""
    chars = [c for c in text if c.strip()][:6] or ["店"]
    fs = min(size, (height - 10) / (len(chars) * 1.12))
    step = fs * 1.12
    y0 = top + (height - step * len(chars)) / 2 + step / 2
    return "".join(f'<text class="sg" x="{cx}" y="{y0 + k * step:.1f}" text-anchor="middle" dominant-baseline="central" '
                   f'font-size="{fs:.1f}">{html.escape(c)}</text>' for k, c in enumerate(chars))


def street(mset: dict, name: str, drawable, seed: str = "", key: str = "default", parts: list[str] | None = None,
           night: bool = False, short: str = "") -> str:
    """巷子裡（晚上）：中間是這家店所在的三層老公寓（樓上鐵窗、一樓鐵捲門拉起一半、裡面亮著燈），
    側面掛一塊直式招牌寫店名；左右是鄰居、路燈與一台機車。和關於我們白天的店面是同一家店，但換了一個角度，
    整頁不會出現兩張一樣的店面。"""
    rnd = random.Random(seed + "street")
    far = name if len(name) <= 6 else (short or name[:4])  # 直式招牌最多 6 個字
    c = mset.get("c", mset["a"])
    left_w = "".join(f'<rect class="fine" x="{x}" y="{y}" width="24" height="26"/>' for x in (22, 58) for y in (128, 170, 212))
    grille = "".join(f"M{x} 168v34" for x in range(288, 380, 8))
    up = "".join(f'<rect x="{x}" y="{y}" width="40" height="30"/><path class="fine" d="{"".join(f"M{x + k} {y}v30" for k in range(8, 40, 8))}"/>'
                 for x in (134, 196) for y in (86, 146))
    shutter = "".join(f"M140 {y}h90" for y in range(210, 226, 4))
    lines = (
        '<path d="M0 266H400"/><path class="fine" d="M0 278H400"/>'
        '<path d="M8 266V110h86v156"/><path class="fine" d="M4 110h94"/>' + left_w
        + '<path d="M118 266V64h134v202"/><path class="fine" d="M114 64h142M118 132h134M118 192h134"/>' + up
        + '<rect x="140" y="206" width="90" height="60"/><path class="fine" d="' + shutter + '"/>'
        + '<path class="fine" d="M146 266v-30h20v30M202 266v-30h22v30"/>'
        + _place(c, 185, 252, 18, 26)
        + '<path class="fine" d="M118 104h-12M118 186h-12"/><rect x="88" y="96" width="22" height="98" rx="2"/>'
        + '<path d="M268 266V128h124v138"/><path class="fine" d="M264 128h132"/>'
        f'<rect x="282" y="164" width="96" height="42"/><path class="fine" d="{grille}"/>'
        '<rect class="fine" x="290" y="222" width="34" height="44"/>'
        '<path d="M50 266V146h16"/><path class="acc" d="M62 146h14l-3 8h-8z"/>'
        '<circle cx="300" cy="256" r="9"/><circle cx="354" cy="256" r="9"/>'
        '<path d="M288 250c0-14 9-22 22-22h10c4 0 6 3 6 7v15z"/><path d="M296 222h26"/><path d="M326 250h14"/>'
        '<path d="M340 250c4-10 4-22-2-34"/><path d="M336 214h14"/><path class="fine" d="M344 226l10 30"/>'
        f'<path class="fine" d="M{rnd.randint(160, 230)} 40q6-6 12 0q6-6 12 0"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><rect x="8" y="110" width="86" height="156"/>'
            '<rect x="118" y="64" width="134" height="202"/><rect x="268" y="128" width="124" height="138"/></g>'
            '<path class="acc" d="M288 250c0-14 9-22 22-22h10c4 0 6 3 6 7v15z"/>')
    lit = ('<g class="sc-paper"><rect x="140" y="226" width="90" height="40"/><rect x="88" y="96" width="22" height="98" rx="2"/>'
           + "".join(f'<rect x="{x}" y="{y}" width="40" height="30"/>' for x, y in ((196, 86), (134, 146))) + '</g>')
    sky = ""
    if night:  # 晚上：月亮、幾顆星、店門口打出來的一片光
        stars = "".join(f'<circle cx="{rnd.randint(20, 380)}" cy="{rnd.randint(14, 56)}" r="{rnd.choice((1, 1.3, 1.6))}"/>' for _ in range(14))
        sky = f'<g class="star">{stars}</g><path class="beam" d="M140 266h90l26 20H114z"/><path class="beam" d="M62 154h14l26 112H36z"/>'
    # 門口依類別放一樣東西：髮廊的旋轉燈、餐飲的立牌、寵物的腳印招牌、鍋物的燈籠，其他放一盆植物
    uid = rnd.randint(1000, 9999)
    room, style = ROOM_OF.get(key, ""), STYLE_OF.get(key, "awning")
    prop_defs = prop_fill = ""
    if room == "salon":
        stripes = "".join(f'<path d="M238 {y}l10-6v5l-10 6z"/>' for y in range(210, 276, 12))
        prop_defs = f'<clipPath id="bp{uid}"><rect x="238" y="214" width="10" height="40" rx="5"/></clipPath>'
        prop_fill = f'<g clip-path="url(#bp{uid})"><g class="pole acc">{stripes}</g></g>'
        prop = '<rect x="238" y="214" width="10" height="40" rx="5"/><path d="M236 214h14M236 254h14M243 254v12"/><circle cx="243" cy="209" r="4"/>'
    elif room == "grooming":
        prop_fill = '<circle class="sc-paper" cx="99" cy="214" r="12"/>' + f'<g class="acc">{_place(mset["a"], 99, 222, 14, 16)}</g>'
        prop = '<path class="fine" d="M99 194v8"/><circle cx="99" cy="214" r="12"/>'
    elif style == "noren":
        prop_fill = '<ellipse class="acc" cx="128" cy="202" rx="8" ry="10"/><ellipse class="acc" cx="242" cy="202" rx="8" ry="10"/>'
        prop = ('<path class="fine" d="M128 192v0M242 192v0"/><ellipse cx="128" cy="202" rx="8" ry="10"/><ellipse cx="242" cy="202" rx="8" ry="10"/>'
                '<path class="fine" d="M120 202h16M234 202h16M128 212v6M242 212v6"/>')
    elif style == "awning":
        prop = ('<path d="M236 266l5-30h20l5 30"/><rect x="240" y="240" width="22" height="18" rx="1"/>'
                '<path class="fine" d="M244 246h14M244 251h10"/>')
        prop_fill = '<rect class="sc-paper" x="240" y="240" width="22" height="18" rx="1"/>'
    else:
        prop = ('<path d="M238 266l3-16h18l3 16"/><path class="fine" d="M250 250c-2-12-8-18-14-20M250 250c1-14 6-20 13-22M250 250c-6-6-6-14-2-20"/>')
    return (f'<defs>{prop_defs}</defs>' if prop_defs else '') + (
            '<rect class="sc-bg" width="400" height="300"/><circle class="acc2" cx="340" cy="52" r="22"/>' + sky + tone + lit + prop_fill
            + f'<g class="sc-ln">{drawable(lines + prop)}</g>' + _vsign(far, 99, 96, 98))


# 髮型手帖：沒有作品照時，用線條畫出常剪的幾種髮型（半身、正面、不畫五官；頭髮後層一塊淡色，臉蓋在上面，再畫瀏海）
_BUST = "<path d='M18 150c3-22 20-32 42-32s39 10 42 32'/><path d='M52 104v14M68 104v14'/>"
_FACE = ("<path class='sk' d='M42 74c0-18 8-30 18-30s18 12 18 30-8 32-18 32-18-14-18-32z'/>"
         "<path d='M42 74c0-18 8-30 18-30s18 12 18 30-8 32-18 32-18-14-18-32z'/>"
         "<path class='fine' d='M50 76c2 2 6 2 8 0M62 76c2 2 6 2 8 0M60 80c-1 4-2 6 1 7M56 94c2 2 6 2 8 0'/>")
_HAIR = {  # (後層：色塊與外輪廓, 前層：瀏海與髮絲)
 "bob": ("<path class='acc2' d='M34 98c-6-40 4-68 26-68s32 28 26 68z'/><path d='M34 98c-6-40 4-68 26-68s32 28 26 68'/><path d='M34 98h10M76 98h10'/>",
         "<path d='M42 62c10-12 26-16 37-6'/><path class='fine' d='M41 66c-2 12-1 22 1 32M79 66c2 12 1 22-1 32'/>"),
 "layer": ("<path class='acc2' d='M32 136c-8-30-6-58 0-78 6-20 16-28 28-28s22 8 28 28c6 20 8 48 0 78-6-8-12-10-16-22l-2 14c-6-10-10-24-10-40H58c0 16-4 30-10 40l-2-14c-4 12-10 14-14 22z'/><path d='M32 136c-8-30-6-58 0-78 6-20 16-28 28-28s22 8 28 28c6 20 8 48 0 78'/><path d='M32 136c4-8 10-10 14-22M88 136c-4-8-10-10-14-22'/>",
           "<path d='M44 56c4-8 10-12 16-12M76 56c-4-8-10-12-16-12'/><path class='fine' d='M40 92c2 12 5 22 8 30M80 92c-2 12-5 22-8 30'/>"),
 "wave": ("<path class='acc2' d='M30 112c-8-6-6-16 0-20-8-8-4-18 2-20-4-10 2-20 10-20 2-10 12-16 18-14 6-2 16 4 18 14 8 0 14 10 10 20 6 2 10 12 2 20 6 4 8 14 0 20c-4 6-11 6-15 0-4 6-11 6-15 0-4 6-11 6-15 0-4 6-11 6-15 0z'/><path d='M30 112c-8-6-6-16 0-20-8-8-4-18 2-20-4-10 2-20 10-20 2-10 12-16 18-14 6-2 16 4 18 14 8 0 14 10 10 20 6 2 10 12 2 20 6 4 8 14 0 20c-4 6-11 6-15 0-4 6-11 6-15 0-4 6-11 6-15 0-4 6-11 6-15 0'/>",
          "<path d='M43 58c4-6 10-8 17-8 6 0 12 2 17 8'/><path class='fine' d='M36 84c4-4 4-10 0-14M84 84c-4-4-4-10 0-14'/>"),
 "crop": ("<path class='acc2' d='M40 76c-3-24 6-40 20-40s23 14 20 40z'/><path d='M40 76c-3-24 6-40 20-40s23 14 20 40'/>",
          "<path d='M44 58c8 2 22 0 32-8'/><path class='fine' d='M41 72v12M79 72v12'/>"),
}


def hairstyle(kind: str) -> str:
    back, front = _HAIR.get(kind, _HAIR["bob"])
    return _BUST + back + _FACE + front


def salon_stage(mset: dict, drawable) -> str:
    """沙龍首屏（桌機）的舞台：拱形鏡框裡左右各一面高高的拱鏡與一張油壓椅，中間只放低矮的東西（推車、插花小桌、毛巾籃），
    讓店名與按鈕站在兩面鏡子中間。1000x420，地板 y=404；鏡面有一道會跟著捲動滑過的反光。"""
    c = mset.get("c", mset["a"])

    def mirror(x: float) -> str:  # 拱鏡（寬 120，頂 70，底 300）＋檯面＋檯上兩瓶
        return (f'<path d="M{x} 300V130a60 60 0 0 1 120 0v170z"/><path class="fine" d="M{x + 10} 296V132a50 50 0 0 1 100 0v164"/>'
                f'<path class="fine" d="M{x + 26} 120c10-14 30-20 46-14M{x + 20} 200l26-26"/>'
                f'<path d="M{x - 16} 300h152v8H{x - 16}z"/>'
                f'<path d="M{x + 8} 300v-20h9v20M{x + 10} 280v-5h5"/><path d="M{x + 98} 300v-14h12v14"/>')

    def chair(x: float) -> str:  # 油壓椅（中心 x）
        return (f'<path d="M{x - 24} 344V314a12 12 0 0 1 12-12h24a12 12 0 0 1 12 12v30"/>'
                f'<path d="M{x - 32} 344h64a6 6 0 0 1 0 12h-64a6 6 0 0 1 0-12z"/><path class="fine" d="M{x - 38} 334h12M{x + 26} 334h12"/>'
                f'<path d="M{x} 356v24M{x - 12} 372h24"/><path d="M{x - 26} 404c4-14 12-22 26-22s22 8 26 22"/>')

    lines = (
        '<path d="M0 404H1000"/>'
        + _lamp(120, drop=10) + _lamp(880, drop=10)
        + mirror(60) + mirror(820) + chair(120) + chair(880)
        # 左邊最外側一盆高植物，右邊牆上一排層架
        + '<path d="M12 404l4-34h30l4 34z"/><path class="fine" d="M31 370c-4-30-16-46-28-52M31 370c2-36 14-56 30-64M31 370c-8-18-8-38 0-52"/>'
        + '<path d="M954 220h40"/><path class="fine" d="M958 220l4 6M990 220l-4 6"/><path d="M962 220v-16h8v16M976 220v-22h8v22"/>'
        # 中間：推車、插花小桌、毛巾籃（都在 y 300 以下）
        + '<path d="M398 404v-92h60v92"/><path d="M398 312h60M398 348h60M398 384h60"/>'
        '<circle class="fine" cx="404" cy="406" r="3"/><circle class="fine" cx="452" cy="406" r="3"/>'
        + _place(c, 428, 348, 28, 32)
        + '<path d="M520 352h96"/><path d="M532 352v52M604 352v52"/><path class="fine" d="M532 378h72"/>'
        '<path d="M560 352l-4-22h18l-4 22"/><path class="fine" d="M565 330c-2-14-10-22-18-26M565 330c0-16 4-26 12-32M565 330c4-12 12-18 22-20"/>'
        + '<path d="M660 404l6-36h60l6 36"/><path class="fine" d="M664 386h64"/>'
        '<rect x="670" y="352" width="52" height="10" rx="5"/><rect x="676" y="342" width="40" height="10" rx="5"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)">'
            '<path d="M44 300h152v8H44z"/><path d="M804 300h152v8H804z"/>'
            '<path d="M88 344h64a6 6 0 0 1 0 12H88a6 6 0 0 1 0-12z"/><path d="M848 344h64a6 6 0 0 1 0 12h-64a6 6 0 0 1 0-12z"/>'
            '<path d="M398 312h60v92h-60z"/><path d="M660 404l6-36h60l6 36z"/></g>')
    glass_d = "M60 300V130a60 60 0 0 1 120 0v170zM820 300V130a60 60 0 0 1 120 0v170z"
    glass = f'<g class="sc-paper"><path d="{glass_d}"/></g>'
    glint = (f'<clipPath id="stageGlass"><path d="{glass_d}"/></clipPath>'
             '<g clip-path="url(#stageGlass)"><g class="glint"><path d="M20 300L110 70h22L42 300z"/><path d="M780 300L870 70h22L802 300z"/></g></g>')
    seats = ('<path class="acc2" d="M88 344h64a6 6 0 0 1 0 12H88a6 6 0 0 1 0-12z"/>'
             '<path class="acc2" d="M848 344h64a6 6 0 0 1 0 12h-64a6 6 0 0 1 0-12z"/>'
             '<rect class="acc2" x="670" y="352" width="52" height="10" rx="5"/>')
    return tone + glass + glint + seats + f'<g class="sc-ln">{drawable(lines)}</g>'
