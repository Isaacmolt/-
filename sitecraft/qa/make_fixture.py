"""品質關卡用的「有照片」測試站：sites/_qa-photos/（不進 git、不部署）。

範例站都沒有照片，燈箱、照片圖說與 img/ 路徑這條路平常不會被測到；
這裡用 Pillow 畫六張假照片，套用範例咖啡的資料建一個有照片的版本，讓 qa.js 一起檢查。
"""
from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from build_site import build_one  # noqa: E402
from common import SAMPLE_LEADS_FILE, SITES_DIR, load_config, load_themes, read_leads  # noqa: E402

SLUG = "_qa-photos"


def fake_photo(path: Path, seed: int, w: int = 1200, h: int = 900) -> None:
    rnd = random.Random(seed)
    base = [(rnd.randint(60, 200), rnd.randint(50, 170), rnd.randint(40, 150)) for _ in range(2)]
    img = Image.new("RGB", (w, h), base[0])
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(base[0][i] * (1 - t) + base[1][i] * t) for i in range(3)))
    for _ in range(14):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(40, 260)
        c = tuple(min(255, v + rnd.randint(-60, 80)) for v in base[rnd.randint(0, 1)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    img = img.filter(ImageFilter.GaussianBlur(18))
    img.save(path, "JPEG", quality=78)


def main() -> Path:
    leads = read_leads(SAMPLE_LEADS_FILE)
    src = next(r for r in leads if r["slug"] == "demo-cafe")
    lead = {**src, "slug": SLUG, "demo_url": ""}
    site = SITES_DIR / SLUG
    shutil.rmtree(site, ignore_errors=True)
    (site / "img").mkdir(parents=True)
    names = []
    for i in range(6):
        n = f"{i + 1:02d}.jpg"
        fake_photo(site / "img" / n, i)
        names.append(n)
    content = json.loads((SITES_DIR / "demo-cafe" / "content.json").read_text(encoding="utf-8"))
    content["gallery"] = names
    (site / "content.json").write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    out = build_one(lead, load_config(), load_themes(), demo=True)
    print("fixture:", out)
    return out


if __name__ == "__main__":
    main()
