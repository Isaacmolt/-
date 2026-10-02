#!/usr/bin/env python3
"""
蝦皮分潤 — 收入模型計算器

把「發文量 × 觸及 × 點擊率 × 轉換率 × 客單價 × 分潤率」串起來，估算月分潤，
並對照 config 的目標算出大概幾個月能達標。預設跑保守 / 基準 / 積極三種情境。

所有假設都可以用參數覆蓋，例如：
    python scripts/shopee_roi_calc.py
    python scripts/shopee_roi_calc.py --posts 90 --reach 1500 --ctr 0.03 --cvr 0.04 --aov 600 --pct 3

輸出：shopee-affiliate/reports/income-model.md
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODULE_DIR = BASE_DIR / "shopee-affiliate"
CONFIG_PATH = MODULE_DIR / "config.json"
CONFIG_EXAMPLE_PATH = MODULE_DIR / "config.example.json"
REPORT_PATH = MODULE_DIR / "reports" / "income-model.md"

COMMISSION_CAP_TWD = 500          # 蝦皮單筆分潤上限（YouTube 訂單 800）
WITHDRAW_THRESHOLD_TWD = 500      # 個人戶提領門檻
BIZ_TAX_THRESHOLD_TWD = 50000     # 單月達 5 萬需轉公司戶

# 三種情境：新手頭三個月常見的數字範圍（來源：2026 年多篇實測心得的區間，保守取值）
SCENARIOS = {
    "保守": dict(posts=45, reach=400, ctr=0.015, cvr=0.02, aov=450, pct=1.5, growth=1.10),
    "基準": dict(posts=60, reach=800, ctr=0.025, cvr=0.03, aov=550, pct=3.0, growth=1.20),
    "積極": dict(posts=90, reach=1800, ctr=0.035, cvr=0.04, aov=650, pct=4.0, growth=1.30),
}


def load_config():
    path = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE_PATH
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def estimate(posts, reach, ctr, cvr, aov, pct):
    clicks = posts * reach * ctr
    orders = clicks * cvr
    per_order = min(aov * pct / 100, COMMISSION_CAP_TWD)
    monthly = orders * per_order
    return {
        "clicks": clicks, "orders": orders, "per_order": per_order, "monthly": monthly,
        "hours": posts * 0.5,  # 每篇含選品、拍照、寫文、回留言約 30 分鐘
    }


def months_to_target(first_month, growth, target, max_months=36):
    """假設月分潤以 growth 倍率成長（帳號成長 + 貼文累積長尾），回傳第幾個月達標。"""
    m = first_month
    for i in range(1, max_months + 1):
        if m >= target:
            return i
        m *= growth
    return None


def fmt_money(v):
    return f"NT${v:,.0f}"


def main():
    parser = argparse.ArgumentParser(description="蝦皮分潤收入模型")
    parser.add_argument("--posts", type=int, help="每月貼文數")
    parser.add_argument("--reach", type=float, help="平均每篇觸及")
    parser.add_argument("--ctr", type=float, help="連結點擊率（0.02 = 2%%）")
    parser.add_argument("--cvr", type=float, help="點擊後 7 天內下單率（0.03 = 3%%）")
    parser.add_argument("--aov", type=float, help="平均訂單金額 NT$")
    parser.add_argument("--pct", type=float, help="平均分潤率 %%（1 = 一般、5 = 萬粉、10 = 加碼）")
    args = parser.parse_args()

    cfg = load_config()
    goals = cfg.get("goals", {})
    custom = {k: v for k, v in vars(args).items() if v is not None}

    scenarios = dict(SCENARIOS)
    if custom:
        base = dict(SCENARIOS["基準"])
        base.update(custom)
        scenarios = {"自訂": base, **SCENARIOS}

    results = {name: (s, estimate(**{k: s[k] for k in ("posts", "reach", "ctr", "cvr", "aov", "pct")})) for name, s in scenarios.items()}

    print("=" * 78)
    print("蝦皮分潤 — 收入模型（第一個月，尚未計入帳號成長）")
    print("=" * 78)
    print(f"{'情境':<6}{'貼文':>6}{'觸及':>7}{'CTR':>7}{'CVR':>7}{'客單':>7}{'分潤%':>7}{'月點擊':>9}{'月訂單':>8}{'每單分潤':>10}{'月分潤':>11}")
    for name, (s, r) in results.items():
        print(f"{name:<6}{s['posts']:>6}{s['reach']:>7.0f}{s['ctr']:>7.1%}{s['cvr']:>7.1%}{s['aov']:>7.0f}{s['pct']:>7.1f}"
              f"{r['clicks']:>9.0f}{r['orders']:>8.1f}{r['per_order']:>10.0f}{fmt_money(r['monthly']):>11}")
    print("-" * 78)
    print(f"單筆上限 {fmt_money(COMMISSION_CAP_TWD)}｜提領門檻 {fmt_money(WITHDRAW_THRESHOLD_TWD)}｜單月 {fmt_money(BIZ_TAX_THRESHOLD_TWD)} 需轉公司戶")

    lines = [
        "# 蝦皮分潤 — 收入模型",
        f"_由 scripts/shopee_roi_calc.py 於 {datetime.now():%Y-%m-%d %H:%M} 產生_",
        "",
        "公式：`月分潤 = 貼文數 × 平均觸及 × 點擊率 × 轉換率 × MIN(客單價 × 分潤率, 500)`",
        "",
        "## 第一個月估算",
        "",
        "| 情境 | 貼文/月 | 觸及/篇 | 點擊率 | 轉換率 | 客單價 | 分潤率 | 月點擊 | 月訂單 | 每單分潤 | **月分潤** | 投入時數 |",
        "|------|--------|--------|-------|-------|-------|-------|-------|-------|---------|-----------|---------|",
    ]
    for name, (s, r) in results.items():
        lines.append(f"| {name} | {s['posts']} | {s['reach']:.0f} | {s['ctr']:.1%} | {s['cvr']:.1%} | {s['aov']:.0f} | {s['pct']:.1f}% "
                     f"| {r['clicks']:.0f} | {r['orders']:.1f} | {fmt_money(r['per_order'])} | **{fmt_money(r['monthly'])}** | {r['hours']:.0f} 小時 |")
    lines += ["", "## 幾個月能達標？", "", "假設每月分潤隨帳號成長與舊貼文長尾累積而成長（保守 ×1.10 / 基準 ×1.20 / 積極 ×1.30）。", ""]
    goal_items = [(k.replace("_commission_twd", "").replace("month_", "第 ") + " 個月目標", v) for k, v in goals.items()]
    header = "| 情境 | 月成長率 | " + " | ".join(f"{k}（{fmt_money(v)}）" for k, v in goal_items) + " |"
    lines.append(header)
    lines.append("|------|---------|" + "|".join("---" for _ in goal_items) + "|")
    print()
    print("達標月數（目標來自 config goals）：")
    for name, (s, r) in results.items():
        cells = []
        for _, target in goal_items:
            m = months_to_target(r["monthly"], s["growth"], target)
            cells.append(f"第 {m} 個月" if m else "36 個月內達不到")
        lines.append(f"| {name} | ×{s['growth']:.2f} | " + " | ".join(cells) + " |")
        print(f"  {name}: " + "、".join(f"{k}→{c}" for (k, _), c in zip(goal_items, cells)))
    lines += [
        "",
        "## 怎麼看這張表",
        "",
        "- **分潤率是最大槓桿。** 一般創作者 1% 幾乎不可能靠量做起來；靠「加碼商品 10%」與「賣家加碼」把平均拉到 3-5% 才有意義。選品時優先挑後台標示加碼的商品。",
        "- **客單價 × 分潤率要靠近 500 上限。** NT$5,000 的家電 10% = 500 就是天花板，再貴也沒用；NT$300 小物 10% 只有 30，要 17 筆才抵一筆家電。",
        "- **觸及是第二槓桿。** Threads 新帳號前 30 篇觸及通常只有幾十到幾百，這張表的保守情境就是這個階段。不要在第一個月就下結論。",
        "- **單月分潤接近 5 萬時要提前準備公司戶**，不然會被卡款。詳見 `05-請款稅務與合規.md`。",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n報告已寫入：{REPORT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
