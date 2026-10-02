#!/usr/bin/env python3
"""
蝦皮分潤助手 — 單檔打包

把 app/index.html + app.css + app.js + data.js 合成一個檔案：
    --artifact   給 claude.ai Artifact 用（沒有 doctype/html/head/body，交由平台包殼；資料內嵌；不走 fetch）
    --standalone 完整單檔 HTML，可直接雙擊或寄給別人

用法：
    python scripts/shopee_app_bundle.py --artifact  --out /path/to/artifact.html
    python scripts/shopee_app_bundle.py --standalone --out /path/to/bundle.html
"""

import argparse
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP = BASE_DIR / "shopee-affiliate" / "app"


def body_inner(html):
    m = re.search(r"<body>(.*)</body>", html, re.S)
    inner = m.group(1)
    inner = re.sub(r'\s*<script src="[^"]+"></script>', "", inner)
    return inner.strip()


def build(mode):
    html = (APP / "index.html").read_text(encoding="utf-8")
    css = (APP / "app.css").read_text(encoding="utf-8")
    js = (APP / "app.js").read_text(encoding="utf-8")
    data = (APP / "data.js").read_text(encoding="utf-8")
    for name, src in (("app.js", js), ("data.js", data), ("app.css", css)):
        if "</script" in src or "</style" in src:
            raise SystemExit(f"{name} 含有 </script 或 </style，不能內嵌")
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    inner = body_inner(html)
    parts = [f"<title>{title}</title>", f"<style>\n{css}\n</style>", inner]
    if mode == "artifact":
        parts.append("<script>window.ARTIFACT_BUILD = true;</script>")
        # artifact 檢視器不允許頁面自行觸發下載，按鈕已隱藏；函式本體也換成提示，避免殘留 download 連結
        js = re.sub(r"function download\(filename, text\) \{.*?\n\}", "function download() { toast(\"請用「複製全部」\"); }", js, count=1, flags=re.S)
    parts.append(f"<script>\n{data}\n</script>")
    parts.append(f"<script>\n{js}\n</script>")
    content = "\n".join(parts) + "\n"
    if mode == "standalone":
        content = ('<!DOCTYPE html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                   '<meta name="theme-color" content="#2d5f2d">\n</head>\n<body>\n' + content + "</body>\n</html>\n")
    return content


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--artifact", action="store_true")
    g.add_argument("--standalone", action="store_true")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    content = build("artifact" if a.artifact else "standalone")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"已輸出 {out}（{len(content.encode('utf-8')) / 1024:.0f} KB）")


if __name__ == "__main__":
    main()
