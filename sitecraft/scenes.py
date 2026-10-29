"""場景插畫：把每個類別的物件放進幾個固定的場景（店面、吧台、窗邊、街角）。

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


def _sign_text(name: str, cx: float, cy: float, width: float, size: float = 24) -> str:
    n = max(len(name), 1)
    fs = min(size, width / (n * 1.02))
    return (f'<text class="sg" x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" '
            f'font-size="{fs:.1f}">{html.escape(name)}</text>')


def storefront(mset: dict, name: str, drawable, ground: bool = True, bg: bool = True) -> str:
    """店面：招牌寫店名、條紋遮陽棚、櫥窗上貼著這個類別的主圖騰、門、吊牌、門口一盆植物。"""
    a, c = mset["a"], mset.get("c", mset["a"])
    stripes = "".join(
        f'<path class="acc" d="M{92 + 27 * i} 126h27l{(76 + 31 * (i + 1)) - (92 + 27 * (i + 1))} 24h-31z"/>'
        for i in range(0, 8, 2))
    scallops = "M76 150" + "a15.5 10 0 0 0 31 0" * 8
    lines = (
        ('<path d="M0 266H400"/><path class="fine" d="M16 280h56M104 280h28M268 280h48M344 280h40"/>' if ground else "")
        + '<path d="M70 266V70h260v196"/><path d="M62 62h276v8H62z"/>'
        + '<rect x="104" y="80" width="192" height="36" rx="4"/>'
        + '<path d="M92 126h216l16 24H76z"/>' + f'<path class="fine" d="{scallops}"/>'
        + '<rect x="94" y="168" width="136" height="82" rx="2"/><path d="M88 250h148"/>'
        + '<path class="fine" d="M104 184l14-10M106 198l26-18"/>'
        + _place(a, 162, 242, 58, 96)
        + '<rect x="246" y="164" width="60" height="102" rx="2"/><path class="fine" d="M256 232v-38a20 20 0 0 1 40 0v38z"/>'
        + '<circle class="acc" cx="297" cy="240" r="3.2"/><path class="fine" d="M240 266v-4h72v4"/>'
        + '<path class="fine" d="M330 132h26M350 132v2"/><circle cx="350" cy="152" r="17"/>' + _place(c, 350, 162, 18, 24)
        + '<path d="M26 266l4-24h32l4 24z"/><path class="fine" d="M46 242c-2-22-14-34-26-38M46 242c2-24 12-38 26-44M46 242c-8-14-6-28 2-38"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><rect x="70" y="70" width="260" height="196"/>'
            '<path d="M26 266l4-24h32l4 24z"/><circle cx="350" cy="152" r="17"/></g>')
    paper = ('<g class="sc-paper"><rect x="104" y="80" width="192" height="36" rx="4"/><rect class="win" x="94" y="168" width="136" height="82" rx="2"/></g>'
             '<rect class="glow" x="94" y="168" width="136" height="82" rx="2"/>')
    # 門上的小牌子：頁面判斷營業中／休息中後由 JS 寫字（沒有 JS 就不顯示）
    plate = ('<g class="plate"><path class="sc-ln-fine" d="M266 176l10-8 10 8"/><rect x="254" y="176" width="44" height="18" rx="3"/>'
             '<text x="276" y="185.5" text-anchor="middle" dominant-baseline="central" font-size="10"></text></g>')
    return ((('<rect class="sc-bg" width="400" height="300"/><circle class="acc2" cx="356" cy="40" r="22"/>') if bg else "")
            + tone + paper + stripes + f'<g class="sc-ln">{drawable(lines)}</g>' + _sign_text(name, 200, 99, 172) + plate)


def counter(mset: dict, drawable) -> str:
    """吧台／工作檯：兩盞吊燈、牆上的畫框與層架，檯面上是這個類別的工具與小物。"""
    b, c = mset.get("b", mset["a"]), mset.get("c", mset["a"])
    lines = (
        '<path class="fine" d="M110 0v46M290 0v46"/>'
        '<path d="M88 70c0-14 10-24 22-24s22 10 22 24zM268 70c0-14 10-24 22-24s22 10 22 24z"/>'
        '<path class="fine" d="M102 76a8 5 0 0 0 16 0M282 76a8 5 0 0 0 16 0"/>'
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


def street(mset: dict, name: str, drawable, seed: str = "") -> str:
    """街角：自己的店在兩棟鄰居中間（鄰居有鐵窗），門口停一台機車，路燈與小鳥。"""
    rnd = random.Random(seed + "street")
    shop = storefront(mset, name, drawable, ground=False, bg=False)
    sx = 0.56
    tx, ty = 112 - 70 * sx, 266 - 266 * sx
    left_w = "".join(f'<rect class="fine" x="{x}" y="{y}" width="24" height="26"/>' for x in (24, 62) for y in (128, 170, 212))
    grille = "".join(f'M{x} 168v34' for x in range(288, 380, 8))
    lines = (
        '<path d="M0 266H400"/><path class="fine" d="M0 278H400"/>'
        '<path d="M10 266V110h92v156"/><path class="fine" d="M6 110h100"/>' + left_w
        + '<path d="M268 266V128h124v138"/><path class="fine" d="M264 128h132"/>'
        f'<rect x="282" y="164" width="96" height="42"/><path class="fine" d="{grille}"/>'
        '<rect class="fine" x="290" y="222" width="34" height="44"/><rect class="fine" x="338" y="222" width="34" height="30"/>'
        '<path d="M107 266V140h-18"/><path class="acc" d="M82 140h14l-3 8h-8z"/>'
        '<circle cx="300" cy="256" r="9"/><circle cx="354" cy="256" r="9"/>'
        '<path d="M288 250c0-14 9-22 22-22h10c4 0 6 3 6 7v15z"/><path d="M296 222h26"/><path d="M326 250h14"/>'
        '<path d="M340 250c4-10 4-22-2-34"/><path d="M336 214h14"/><path class="fine" d="M344 226l10 30"/>'
        f'<path class="fine" d="M{rnd.randint(180, 230)} 46q6-6 12 0q6-6 12 0M{rnd.randint(140, 170)} 60q5-5 10 0q5-5 10 0"/>'
    )
    tone = ('<g class="sc-tone" transform="translate(7 7)"><rect x="10" y="110" width="92" height="156"/>'
            '<rect x="268" y="128" width="124" height="138"/></g>'
            '<path class="acc" d="M288 250c0-14 9-22 22-22h10c4 0 6 3 6 7v15z"/>')
    return ('<rect class="sc-bg" width="400" height="300"/><circle class="acc2" cx="340" cy="58" r="24"/>' + tone
            + f'<g transform="translate({tx:.1f} {ty:.1f}) scale({sx})" style="--k:{1 / sx:.2f}">{shop}</g>'
            + f'<g class="sc-ln">{drawable(lines)}</g>')

