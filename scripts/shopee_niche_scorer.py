#!/usr/bin/env python3
"""
蝦皮分潤 — 利基方向評分器
讀取 shopee-affiliate/niches.json，依權重計算每個利基的加權分數，
輸出排名表到終端機與 shopee-affiliate/reports/niche-ranking.md。

用法：
    python scripts/shopee_niche_scorer.py            # 全部排名
    python scripts/shopee_niche_scorer.py --top 3    # 只看前 3 名
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
NICHES_PATH = BASE_DIR / "shopee-affiliate" / "niches.json"
REPORT_PATH = BASE_DIR / "shopee-affiliate" / "reports" / "niche-ranking.md"


def load_niches():
    with open(NICHES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def weighted_score(scores, weights):
    """加權平均，回傳 0-5 分（四捨五入到小數 2 位）。"""
    total_w = sum(weights.values())
    s = sum(scores.get(k, 0) * w for k, w in weights.items())
    return round(s / total_w, 2)


def rank(data):
    weights = data["weights"]
    ranked = []
    for n in data["niches"]:
        n = dict(n)
        n["score"] = weighted_score(n["scores"], weights)
        # 找出最強與最弱的面向，方便一眼看出為什麼
        labels = data["criteria_labels"]
        best = max(n["scores"], key=n["scores"].get)
        worst = min(n["scores"], key=n["scores"].get)
        n["best"] = labels[best]
        n["worst"] = labels[worst]
        ranked.append(n)
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def stars(v):
    return "★" * int(v) + "☆" * (5 - int(v))


def build_markdown(data, ranked, top=None):
    labels = data["criteria_labels"]
    weights = data["weights"]
    shown = ranked[:top] if top else ranked
    lines = []
    lines.append("# 利基方向排名")
    lines.append(f"_由 scripts/shopee_niche_scorer.py 於 {datetime.now():%Y-%m-%d %H:%M} 產生_")
    lines.append("")
    lines.append("## 權重")
    lines.append("")
    lines.append("| 面向 | 權重 |")
    lines.append("|------|------|")
    for k, w in weights.items():
        lines.append(f"| {labels[k]} | {w:.0%} |")
    lines.append("")
    lines.append("## 排名")
    lines.append("")
    header = "| # | 利基 | 總分 | " + " | ".join(labels[k] for k in weights) + " | 最強 | 最弱 |"
    sep = "|---|------|------|" + "|".join("---" for _ in weights) + "|------|------|"
    lines.append(header)
    lines.append(sep)
    for i, n in enumerate(shown, 1):
        cells = " | ".join(str(n["scores"][k]) for k in weights)
        lines.append(f"| {i} | {n['name']} | **{n['score']}** | {cells} | {n['best']} | {n['worst']} |")
    lines.append("")
    lines.append("## 每個利基的重點")
    lines.append("")
    for i, n in enumerate(shown, 1):
        lines.append(f"### {i}. {n['name']}（{n['score']} 分）")
        lines.append(f"- **受眾：** {n['audience']}")
        lines.append(f"- **價格帶：** {n['price_band']}")
        lines.append(f"- **商品例子：** {'、'.join(n['example_products'])}")
        lines.append(f"- **備註：** {n['notes']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="蝦皮分潤利基評分器")
    parser.add_argument("--top", type=int, default=None, help="只顯示前 N 名")
    args = parser.parse_args()

    data = load_niches()
    ranked = rank(data)

    print("=" * 70)
    print("蝦皮分潤 — 利基方向排名")
    print("=" * 70)
    shown = ranked[: args.top] if args.top else ranked
    for i, n in enumerate(shown, 1):
        print(f"{i:>2}. {n['score']:.2f}  {stars(round(n['score']))}  {n['name']}")
        print(f"     最強：{n['best']}　最弱：{n['worst']}")
    print("=" * 70)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_markdown(data, ranked, args.top), encoding="utf-8")
    print(f"報告已寫入：{REPORT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
