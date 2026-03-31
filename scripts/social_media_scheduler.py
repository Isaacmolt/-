#!/usr/bin/env python3
"""
SheetCraft AI — Social Media Post Generator & Scheduler
Reads templates, product catalog, and SEO keywords to auto-generate
scheduled social media posts for 30 days.
"""

import json
import csv
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE_DIR / "catalog.json"
TEMPLATES_PATH = BASE_DIR / "marketing" / "social-media-templates.md"
KEYWORDS_PATH = BASE_DIR / "marketing" / "etsy-seo-keywords.md"
OUTPUT_DIR = BASE_DIR / "marketing" / "scheduled-posts"
CALENDAR_PATH = BASE_DIR / "marketing" / "content-calendar.md"

# ── Helpers ──────────────────────────────────────────────────────────

def load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_keywords():
    """Parse etsy-seo-keywords.md and return a dict of keyword lists by category."""
    text = KEYWORDS_PATH.read_text(encoding="utf-8")
    keywords = {
        "finance": [],
        "business": [],
        "productivity": [],
        "general": [],
    }
    # Grab all lines that start with "- "
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            kw = line[2:].strip()
            # Split comma-separated keywords
            for k in kw.split(","):
                k = k.strip()
                if k:
                    keywords["general"].append(k)
    return keywords


def keywords_to_hashtags(keyword_list, limit=10):
    """Convert keyword phrases to #hashtag format."""
    tags = set()
    for kw in keyword_list:
        tag = "#" + re.sub(r"[^a-zA-Z0-9]", "", kw.title().replace(" ", ""))
        tags.add(tag)
        if len(tags) >= limit:
            break
    return sorted(tags)


def get_product_hashtags(product, all_keywords):
    """Build hashtag list from product tags + global keywords."""
    base_tags = [
        "#GoogleSheets", "#SpreadsheetTemplate", "#DigitalDownload",
        "#SheetCraftAI", "#PassiveIncome",
    ]
    product_tags = ["#" + re.sub(r"[^a-zA-Z0-9]", "", t.title().replace(" ", ""))
                     for t in product.get("tags", [])]
    category_map = {
        "Personal Finance": ["#PersonalFinance", "#Budgeting", "#MoneyTips", "#FinancialPlanner"],
        "Freelancer": ["#Freelancer", "#FreelanceLife", "#SelfEmployed", "#SideHustle"],
        "Business": ["#SmallBusiness", "#Entrepreneur", "#BusinessTools", "#Startup"],
        "Productivity": ["#Productivity", "#GoalSetting", "#HabitTracker", "#GetThingsDone"],
    }
    cat_tags = category_map.get(product.get("category", ""), [])
    extra = keywords_to_hashtags(all_keywords["general"], limit=5)
    combined = list(dict.fromkeys(base_tags + product_tags + cat_tags + extra))
    return combined[:15]


# ── Feature descriptions per product ────────────────────────────────

PRODUCT_FEATURES = {
    "Monthly Budget Tracker": [
        "Auto-calculated income vs expenses",
        "Visual dashboard with charts",
        "Category-level spending breakdown",
    ],
    "Annual Financial Overview": [
        "12-month financial summary at a glance",
        "Net worth tracking over time",
        "Year-over-year comparison charts",
    ],
    "Freelancer Income Tracker": [
        "Invoice tracking & payment status",
        "Quarterly tax estimation",
        "Client-by-client revenue breakdown",
    ],
    "Debt Payoff Planner": [
        "Snowball & avalanche methods built in",
        "Payoff timeline calculator",
        "Interest savings tracker",
    ],
    "50/30/20 Budget Template": [
        "Auto-split into Needs / Wants / Savings",
        "Visual progress bars for each category",
        "Monthly trend tracking",
    ],
    "Small Business P&L": [
        "Revenue & expense tracking by category",
        "Monthly P&L statement auto-generated",
        "Profit margin calculations",
    ],
    "Inventory Manager": [
        "Real-time stock level tracking",
        "Low-stock alerts",
        "SKU-based product management",
    ],
    "Client CRM Tracker": [
        "Sales pipeline visualization",
        "Client contact & status management",
        "Follow-up reminders & deal tracking",
    ],
    "Annual Habit Tracker": [
        "365-day visual habit grid",
        "Streak counter & completion rate",
        "Multiple habits on one sheet",
    ],
    "Project Management Board": [
        "Kanban-style task board",
        "Gantt chart timeline view",
        "Team assignment & progress tracking",
    ],
}


# ── Post generators (5 styles per product) ───────────────────────────

def generate_style_a(product, features, hashtags):
    """Product showcase"""
    name = product["name"]
    price = product["price"]
    f1, f2, f3 = features
    tags = " ".join(hashtags[:10])
    return (
        f"Stop spending hours building spreadsheets from scratch.\n\n"
        f"I made a {name} that does everything automatically:\n"
        f"  {f1}\n"
        f"  {f2}\n"
        f"  {f3}\n\n"
        f"Just enter your numbers. The template handles the rest.\n\n"
        f"Link in bio  ${price:.2f}\n\n"
        f"{tags}"
    )


def generate_style_b(product, features, hashtags):
    """Pain point -> solution"""
    name = product["name"]
    tags = " ".join(hashtags[:10])
    return (
        f"You: spending 3 hours making a {name.lower()} from scratch\n"
        f"Me: using a template that took 3 minutes to set up\n\n"
        f"The difference? Automatic formulas, beautiful charts, and zero headaches.\n\n"
        f"Available now  link in bio\n\n"
        f"{tags}"
    )


def generate_style_c(product, features, hashtags):
    """Data / results showcase"""
    name = product["name"]
    tags = " ".join(hashtags[:10])
    return (
        f"This month's numbers:\n"
        f"  Income: tracked automatically\n"
        f"  Savings rate: up 12%\n"
        f"  Time spent on spreadsheets: 5 minutes\n\n"
        f"All tracked automatically with my {name}.\n\n"
        f"No apps. No subscriptions. Just Google Sheets.\n\n"
        f"Grab yours  link in bio\n\n"
        f"{tags}"
    )


def generate_style_d(product, features, hashtags):
    """Educational / How-to"""
    name = product["name"]
    tags = " ".join(hashtags[:10])
    return (
        f"How to get organized with your {name.lower().replace('template', '').strip()} (without willpower):\n\n"
        f"Step 1: Automate the tracking (use a template)\n"
        f"Step 2: Check your dashboard weekly (takes 2 min)\n"
        f"Step 3: Adjust categories monthly\n"
        f"Step 4: Watch your progress grow\n\n"
        f"The hardest part was Step 1.\n"
        f"I already did that for you.\n\n"
        f"Link in bio.\n\n"
        f"{tags}"
    )


def generate_style_e(product, features, hashtags):
    """Limited-time offer"""
    name = product["name"]
    price = product["price"]
    sale_price = round(price * 0.7, 2)
    tags = " ".join(hashtags[:10])
    return (
        f"30% OFF this week only\n\n"
        f"{name}  normally ${price:.2f}, now just ${sale_price:.2f}\n\n"
        f"Beautiful charts. Automatic formulas. Zero headaches.\n\n"
        f"Sale ends Sunday. Don't miss it.\n\n"
        f"Link in bio\n\n"
        f"{tags}"
    )


STYLE_GENERATORS = [
    ("product_showcase", generate_style_a),
    ("pain_point_solution", generate_style_b),
    ("data_results", generate_style_c),
    ("educational", generate_style_d),
    ("limited_offer", generate_style_e),
]


# ── Weekly content calendar mapping ─────────────────────────────────
# 0=Mon ... 6=Sun
DAY_CONTENT = {
    0: ("Product Showcase", "Instagram + Threads", "product_showcase"),
    1: ("Pinterest Pins", "Pinterest", "product_showcase"),
    2: ("Educational Tip", "Instagram + Threads", "educational"),
    3: ("Pinterest Pins", "Pinterest", "educational"),
    4: ("Data / Results Share", "Instagram + Threads", "data_results"),
    5: ("Customer Result / Testimonial", "Instagram + Threads", "pain_point_solution"),
    6: ("Rest / Schedule Next Week", "—", None),
}


# ── Main logic ───────────────────────────────────────────────────────

def main():
    catalog = load_catalog()
    products = catalog["products"]
    all_keywords = load_keywords()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Generate 5 styles per product ────────────────────────────
    for product in products:
        name = product["name"]
        pid = product["id"]
        features = PRODUCT_FEATURES.get(name, ["Feature 1", "Feature 2", "Feature 3"])
        hashtags = get_product_hashtags(product, all_keywords)

        product_dir = OUTPUT_DIR / pid
        product_dir.mkdir(parents=True, exist_ok=True)

        for style_name, generator in STYLE_GENERATORS:
            post_text = generator(product, features, hashtags)
            out_file = product_dir / f"{style_name}.txt"
            out_file.write_text(post_text, encoding="utf-8")

        print(f"  Generated 5 posts for: {name}")

    # ── 2. Build 30-day schedule CSV ────────────────────────────────
    start_date = datetime(2026, 4, 1)
    schedule_rows = []
    product_cycle = 0  # rotate through products

    for day_offset in range(30):
        current_date = start_date + timedelta(days=day_offset)
        weekday = current_date.weekday()  # 0=Mon
        content_type, platform, style_key = DAY_CONTENT[weekday]

        if style_key is None:
            # Rest day
            schedule_rows.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day": current_date.strftime("%A"),
                "platform": platform,
                "content_type": content_type,
                "product": "—",
                "post_file": "—",
                "status": "rest",
            })
            continue

        product = products[product_cycle % len(products)]
        pid = product["id"]
        post_file = f"scheduled-posts/{pid}/{style_key}.txt"

        schedule_rows.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "day": current_date.strftime("%A"),
            "platform": platform,
            "content_type": content_type,
            "product": product["name"],
            "post_file": post_file,
            "status": "scheduled",
        })
        product_cycle += 1

    csv_path = OUTPUT_DIR / "schedule.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "day", "platform", "content_type", "product", "post_file", "status"
        ])
        writer.writeheader()
        writer.writerows(schedule_rows)

    print(f"  Schedule CSV written: {csv_path}")

    # ── 3. Generate content-calendar.md ─────────────────────────────
    lines = [
        "# SheetCraft AI — 30-Day Content Calendar",
        f"_Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        f"_Period: 2026-04-01 to 2026-04-30_\n",
        "| Date | Day | Platform | Content Type | Product | Status |",
        "|------|-----|----------|-------------|---------|--------|",
    ]
    for row in schedule_rows:
        lines.append(
            f"| {row['date']} | {row['day'][:3]} | {row['platform']} | "
            f"{row['content_type']} | {row['product']} | {row['status']} |"
        )

    lines.append("\n---\n")
    lines.append("## Weekly Theme Guide\n")
    lines.append("| Day | Theme | Platform |")
    lines.append("|-----|-------|----------|")
    lines.append("| Monday | Product Showcase | Instagram + Threads |")
    lines.append("| Tuesday | Pinterest Pins | Pinterest |")
    lines.append("| Wednesday | Educational Tip | Instagram + Threads |")
    lines.append("| Thursday | Pinterest Pins | Pinterest |")
    lines.append("| Friday | Data / Results Share | Instagram + Threads |")
    lines.append("| Saturday | Customer Result / Testimonial | Instagram + Threads |")
    lines.append("| Sunday | Rest / Schedule Next Week | -- |")

    CALENDAR_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Content calendar written: {CALENDAR_PATH}")

    print("\nDone! All social media posts and schedule generated.")


if __name__ == "__main__":
    main()
