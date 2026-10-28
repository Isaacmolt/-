# SheetCraft AI

AI-powered digital product company. We create and sell high-quality Google Sheets & Excel templates.

## Structure

```
├── BUSINESS_PLAN.md          # Full business plan & financial projections
├── OPERATIONS.md             # SOPs, brand guidelines, SEO strategy
├── PRODUCT_ROADMAP.md        # Product pipeline & development status
├── products/
│   └── 01-monthly-budget-tracker/
│       ├── generate_template.py    # Template generator script
│       ├── README.md               # Product specs & listing info
│       ├── listing-description.txt # Etsy/Gumroad product description
│       └── *.xlsx                  # Generated template file
├── scripts/
│   └── requirements.txt      # Python dependencies
├── marketing/
│   ├── etsy-seo-keywords.md  # SEO keyword database
│   └── pricing-strategy.md   # Pricing tiers & promo calendar
└── sitecraft/                # 第二條業務線：在地商家一頁式官網代工（NT$860）
    ├── README.md             # 起床操作指南
    ├── PLAYBOOK.md           # 業務 SOP
    ├── find_leads.py         # Google Places API 找沒官網的店
    ├── build_site.py         # 產生一頁式網站
    ├── send_outreach.py      # 寄信 + 追蹤
    └── crm.py                # 名單管理
```

## Quick Start

```bash
pip install -r scripts/requirements.txt
python products/01-monthly-budget-tracker/generate_template.py
```

## Products

| # | Product | Status | Price |
|---|---------|--------|-------|
| 01 | Monthly Budget Tracker | ✅ Done | $5.99 |
| 02 | Annual Financial Overview | 🔲 Next | $7.99 |
| 03 | Freelancer Income Tracker | 🔲 Planned | $6.99 |
| 04 | Debt Payoff Planner | 🔲 Planned | $4.99 |
| 05 | 50/30/20 Budget Template | 🔲 Planned | $3.99 |

## SiteCraft — 在地商家官網代工

第二條業務線：用 Google Places API 找出地圖上還沒有官網的店家，先免費做好一頁式網站草稿寄給老闆，喜歡就付 NT$860 正式上線（含 1 年主機）。

```bash
pip install -r sitecraft/requirements.txt
python sitecraft/find_leads.py --city 台中市 --district 西區 --type 咖啡廳
python sitecraft/build_site.py
python sitecraft/send_outreach.py --stage first --send
python sitecraft/crm.py due
```

範例站：<https://isaacmolt.github.io/-/sites/>　完整說明：[sitecraft/README.md](sitecraft/README.md)
