#!/usr/bin/env python3
"""
SheetCraft AI — Pinterest Pin Description Generator
Generates 3 unique Pin descriptions per product, optimized for Pinterest SEO.
"""

import json
import re
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE_DIR / "catalog.json"
KEYWORDS_PATH = BASE_DIR / "marketing" / "etsy-seo-keywords.md"
OUTPUT_DIR = BASE_DIR / "marketing" / "pinterest-pins"

# ── Board suggestions by category ───────────────────────────────────
BOARD_MAP = {
    "Personal Finance": "Personal Finance Templates",
    "Freelancer": "Freelancer Tools & Templates",
    "Business": "Small Business Resources",
    "Productivity": "Productivity & Goal Setting",
}

# ── Product feature & audience data ─────────────────────────────────
PRODUCT_DATA = {
    "Monthly Budget Tracker": {
        "audiences": [
            "anyone who wants to take control of their monthly spending",
            "budgeting beginners looking for an easy-to-use tracker",
            "busy professionals who need automated expense tracking",
        ],
        "angles": [
            ("Track Every Dollar Automatically", "budget tracking"),
            ("Beautiful Budget Dashboard", "visual finance"),
            ("Beginner-Friendly Budgeting", "easy budget"),
        ],
        "features": [
            "Auto-calculated income vs expenses",
            "Visual dashboard with charts",
            "Category-level spending breakdown",
        ],
    },
    "Annual Financial Overview": {
        "audiences": [
            "people who want a bird's-eye view of their yearly finances",
            "anyone tracking net worth and long-term financial goals",
            "planners who want to compare their finances year over year",
        ],
        "angles": [
            ("See Your Full Financial Picture", "annual finance"),
            ("Track Your Net Worth Growth", "net worth tracker"),
            ("Year-in-Review Money Dashboard", "financial overview"),
        ],
        "features": [
            "12-month summary at a glance",
            "Net worth tracking over time",
            "Year-over-year comparison charts",
        ],
    },
    "Freelancer Income Tracker": {
        "audiences": [
            "freelancers juggling multiple clients and invoices",
            "self-employed professionals who need tax-ready records",
            "side hustlers tracking project-based income",
        ],
        "angles": [
            ("Freelance Income Made Simple", "freelance finance"),
            ("Tax-Ready Income Records", "freelancer taxes"),
            ("Client Revenue Breakdown", "freelance income"),
        ],
        "features": [
            "Invoice tracking & payment status",
            "Quarterly tax estimation",
            "Client-by-client revenue breakdown",
        ],
    },
    "Debt Payoff Planner": {
        "audiences": [
            "anyone serious about becoming debt-free",
            "people using the snowball or avalanche payoff method",
            "budget-conscious individuals tracking multiple debts",
        ],
        "angles": [
            ("Your Debt-Free Roadmap", "debt payoff"),
            ("Snowball vs Avalanche Calculator", "debt strategy"),
            ("See Your Payoff Date", "debt freedom"),
        ],
        "features": [
            "Snowball & avalanche methods built in",
            "Payoff timeline calculator",
            "Interest savings tracker",
        ],
    },
    "50/30/20 Budget Template": {
        "audiences": [
            "beginners who want a simple budgeting rule to follow",
            "anyone looking to balance needs, wants, and savings",
            "people who struggle with overspending in any category",
        ],
        "angles": [
            ("The Simplest Budget Rule", "50 30 20 budget"),
            ("Needs, Wants & Savings Sorted", "budget categories"),
            ("Visual Budget Progress Bars", "budget tracking"),
        ],
        "features": [
            "Auto-split into Needs / Wants / Savings",
            "Visual progress bars for each category",
            "Monthly trend tracking",
        ],
    },
    "Small Business P&L": {
        "audiences": [
            "small business owners who need clear profit & loss reports",
            "entrepreneurs tracking monthly revenue and expenses",
            "startup founders who want to understand their margins",
        ],
        "angles": [
            ("Know Your Profit Margins", "small business P&L"),
            ("Monthly P&L Auto-Generated", "business accounting"),
            ("Revenue vs Expenses at a Glance", "business finance"),
        ],
        "features": [
            "Revenue & expense tracking by category",
            "Monthly P&L statement auto-generated",
            "Profit margin calculations",
        ],
    },
    "Inventory Manager": {
        "audiences": [
            "small business owners managing physical or digital inventory",
            "Etsy / e-commerce sellers tracking stock levels",
            "warehouse managers who need a lightweight tracking tool",
        ],
        "angles": [
            ("Never Run Out of Stock", "inventory management"),
            ("SKU-Based Stock Tracking", "inventory tracker"),
            ("Low-Stock Alerts Built In", "stock management"),
        ],
        "features": [
            "Real-time stock level tracking",
            "Low-stock alerts",
            "SKU-based product management",
        ],
    },
    "Client CRM Tracker": {
        "audiences": [
            "freelancers and agencies managing client relationships",
            "sales professionals tracking their pipeline",
            "small business owners who want a simple CRM",
        ],
        "angles": [
            ("Simple CRM for Small Teams", "client management"),
            ("Visualize Your Sales Pipeline", "sales tracker"),
            ("Never Lose Track of a Client", "CRM tool"),
        ],
        "features": [
            "Sales pipeline visualization",
            "Client contact & status management",
            "Follow-up reminders & deal tracking",
        ],
    },
    "Annual Habit Tracker": {
        "audiences": [
            "anyone building new daily habits and routines",
            "goal-setters who love tracking streaks",
            "productivity enthusiasts who want visual accountability",
        ],
        "angles": [
            ("365 Days of Habit Building", "habit tracker"),
            ("Streak Counter & Completion Stats", "daily habits"),
            ("Visual Habit Grid for the Whole Year", "habit building"),
        ],
        "features": [
            "365-day visual habit grid",
            "Streak counter & completion rate",
            "Multiple habits on one sheet",
        ],
    },
    "Project Management Board": {
        "audiences": [
            "team leads who need a lightweight project tracker",
            "solopreneurs managing multiple projects at once",
            "anyone who loves Kanban boards but wants it in a spreadsheet",
        ],
        "angles": [
            ("Kanban Board in Google Sheets", "project management"),
            ("Gantt Chart Timeline View", "project planning"),
            ("Track Tasks & Team Progress", "task management"),
        ],
        "features": [
            "Kanban-style task board",
            "Gantt chart timeline view",
            "Team assignment & progress tracking",
        ],
    },
}


def load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_hashtags(product, angle_keyword):
    """Build Pinterest-optimized hashtag string."""
    base = ["#GoogleSheets", "#SpreadsheetTemplate", "#DigitalDownload"]
    cat_map = {
        "Personal Finance": ["#BudgetTemplate", "#PersonalFinance", "#MoneyTips"],
        "Freelancer": ["#FreelancerTools", "#SelfEmployed", "#FreelanceLife"],
        "Business": ["#SmallBusiness", "#Entrepreneur", "#BusinessTools"],
        "Productivity": ["#Productivity", "#GoalSetting", "#HabitTracker"],
    }
    cat_tags = cat_map.get(product.get("category", ""), [])
    kw_tag = "#" + re.sub(r"[^a-zA-Z0-9]", "", angle_keyword.title().replace(" ", ""))
    combined = list(dict.fromkeys(base + cat_tags + [kw_tag]))
    return " ".join(combined[:8])


def generate_pin(product, angle_idx, data):
    """Generate a single Pin description."""
    title_text, angle_kw = data["angles"][angle_idx]
    audience = data["audiences"][angle_idx]
    features = data["features"]
    name = product["name"]
    price = product["price"]
    category = product.get("category", "General")
    board = BOARD_MAP.get(category, "Digital Templates")
    hashtags = build_hashtags(product, angle_kw)

    pin = (
        f"Title: {name} | {title_text} | Google Sheets Template\n\n"
        f"Description:\n"
        f"{name} -- the perfect Google Sheets template for {audience}.\n\n"
        f"What you get:\n"
        f"  {features[0]}\n"
        f"  {features[1]}\n"
        f"  {features[2]}\n\n"
        f"Works in Google Sheets and Excel. No formulas needed -- "
        f"everything calculates automatically!\n\n"
        f"Instant digital download. Only ${price:.2f}.\n\n"
        f"Link: [Etsy listing URL]\n\n"
        f"Board: {board}\n\n"
        f"{hashtags}"
    )
    return pin


def main():
    catalog = load_catalog()
    products = catalog["products"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    for product in products:
        name = product["name"]
        pid = product["id"]
        data = PRODUCT_DATA.get(name)
        if not data:
            print(f"  [skip] No pin data for {name}")
            continue

        product_dir = OUTPUT_DIR / pid
        product_dir.mkdir(parents=True, exist_ok=True)

        for i in range(3):
            pin_text = generate_pin(product, i, data)
            out_file = product_dir / f"pin_{i + 1}.txt"
            out_file.write_text(pin_text, encoding="utf-8")
            total += 1

        print(f"  Generated 3 pins for: {name}")

    print(f"\nDone! {total} Pinterest pin descriptions generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
