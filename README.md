# SheetCraft AI

AI-powered digital product company. We create and sell high-quality Google Sheets & Excel templates.

Two revenue lines:

1. **Templates** — Google Sheets / Excel templates sold on Etsy & Gumroad (this README).
2. **蝦皮分潤 (Shopee Affiliate)** — Taiwan-market affiliate account on Threads / IG. Planning docs, content templates, link tooling and a tracking workbook live in [`shopee-affiliate/`](shopee-affiliate/README.md). Start with [`shopee-affiliate/起床看這裡-蝦皮分潤.md`](shopee-affiliate/起床看這裡-蝦皮分潤.md). Phone/desktop app: https://isaacmolt.github.io/-/shopee-affiliate/app/ (PWA, GitHub-synced data, Threads auto-posting bot).

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
└── shopee-affiliate/         # 蝦皮分潤 business line (docs, templates, tracker, link page)
```

## Quick Start

```bash
pip install -r scripts/requirements.txt
python products/01-monthly-budget-tracker/generate_template.py
```

## Shopee Affiliate quick start

```bash
cp shopee-affiliate/config.example.json shopee-affiliate/config.json
make shopee-all   # niche ranking, link batch sheet + link page, 30-day posts, tracker.xlsx, income model
```

## Products

| # | Product | Status | Price |
|---|---------|--------|-------|
| 01 | Monthly Budget Tracker | ✅ Done | $5.99 |
| 02 | Annual Financial Overview | 🔲 Next | $7.99 |
| 03 | Freelancer Income Tracker | 🔲 Planned | $6.99 |
| 04 | Debt Payoff Planner | 🔲 Planned | $4.99 |
| 05 | 50/30/20 Budget Template | 🔲 Planned | $3.99 |
