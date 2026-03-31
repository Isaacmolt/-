"""
SheetCraft AI — Product Catalog Generator (Agent: 目錄小美 Mei)
Generates a master product catalog with all products and their status.
"""

import os
import glob
import json

PRODUCTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "products")
BUNDLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bundles")
OUTPUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRODUCT_INFO = {
    "01-monthly-budget-tracker": {
        "name": "Monthly Budget Tracker",
        "price": 5.99,
        "category": "Personal Finance",
        "tags": ["budget", "expense tracker", "personal finance", "monthly budget"],
    },
    "02-annual-financial-overview": {
        "name": "Annual Financial Overview",
        "price": 7.99,
        "category": "Personal Finance",
        "tags": ["annual budget", "financial overview", "net worth", "yearly planner"],
    },
    "03-freelancer-income-tracker": {
        "name": "Freelancer Income Tracker",
        "price": 6.99,
        "category": "Freelancer",
        "tags": ["freelancer", "income tracker", "invoice", "tax estimator"],
    },
    "04-debt-payoff-planner": {
        "name": "Debt Payoff Planner",
        "price": 4.99,
        "category": "Personal Finance",
        "tags": ["debt payoff", "snowball", "avalanche", "debt tracker"],
    },
    "05-503020-budget": {
        "name": "50/30/20 Budget Template",
        "price": 3.99,
        "category": "Personal Finance",
        "tags": ["50 30 20", "budget rule", "needs wants savings"],
    },
    "06-small-business-pl": {
        "name": "Small Business P&L",
        "price": 9.99,
        "category": "Business",
        "tags": ["profit loss", "small business", "P&L", "accounting"],
    },
    "07-inventory-manager": {
        "name": "Inventory Manager",
        "price": 8.99,
        "category": "Business",
        "tags": ["inventory", "stock tracker", "warehouse", "SKU"],
    },
    "08-client-crm": {
        "name": "Client CRM Tracker",
        "price": 9.99,
        "category": "Business",
        "tags": ["CRM", "client tracker", "sales pipeline", "customer"],
    },
    "09-habit-tracker": {
        "name": "Annual Habit Tracker",
        "price": 5.99,
        "category": "Productivity",
        "tags": ["habit tracker", "daily routine", "goal tracker", "streak"],
    },
    "10-project-management": {
        "name": "Project Management Board",
        "price": 7.99,
        "category": "Productivity",
        "tags": ["project management", "task tracker", "gantt", "team"],
    },
}

BUNDLES = {
    "Personal_Finance_Bundle": {"name": "Personal Finance Bundle", "price": 19.99, "products": ["01", "02", "04", "05"]},
    "Small_Business_Bundle": {"name": "Small Business Bundle", "price": 24.99, "products": ["06", "07", "08"]},
    "Freelancer_Bundle": {"name": "Freelancer Bundle", "price": 14.99, "products": ["03", "05", "10"]},
    "Ultimate_Productivity_Bundle": {"name": "Ultimate Productivity Bundle", "price": 39.99, "products": ["all"]},
}


def get_product_status(product_dir):
    xlsx_files = glob.glob(os.path.join(PRODUCTS_DIR, product_dir, "*.xlsx"))
    has_generator = os.path.exists(os.path.join(PRODUCTS_DIR, product_dir, "generate_template.py"))
    has_listing = os.path.exists(os.path.join(PRODUCTS_DIR, product_dir, "listing-description.txt"))
    has_readme = os.path.exists(os.path.join(PRODUCTS_DIR, product_dir, "README.md"))

    if xlsx_files and has_listing and has_readme:
        return "ready"
    elif has_generator:
        return "generated" if xlsx_files else "generator_only"
    else:
        return "not_started"


def generate_catalog():
    catalog = {"company": "SheetCraft AI", "products": [], "bundles": [], "summary": {}}

    ready = 0
    total_value = 0

    for product_dir, info in PRODUCT_INFO.items():
        status = get_product_status(product_dir)
        xlsx_files = glob.glob(os.path.join(PRODUCTS_DIR, product_dir, "*.xlsx"))

        product = {
            "id": product_dir,
            "name": info["name"],
            "price": info["price"],
            "category": info["category"],
            "tags": info["tags"],
            "status": status,
            "files": [os.path.basename(f) for f in xlsx_files],
        }
        catalog["products"].append(product)

        if status == "ready":
            ready += 1
        total_value += info["price"]

    for bundle_key, bundle_info in BUNDLES.items():
        zip_path = os.path.join(BUNDLES_DIR, f"{bundle_key}_SheetCraft.zip")
        catalog["bundles"].append({
            "id": bundle_key,
            "name": bundle_info["name"],
            "price": bundle_info["price"],
            "exists": os.path.exists(zip_path),
        })

    catalog["summary"] = {
        "total_products": len(PRODUCT_INFO),
        "ready_products": ready,
        "total_individual_value": round(total_value, 2),
        "total_bundles": len(BUNDLES),
    }

    # Save JSON catalog
    catalog_path = os.path.join(OUTPUT_DIR, "catalog.json")
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"Catalog saved: {catalog_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("  SheetCraft AI — Product Catalog (目錄小美)")
    print("=" * 60)
    print(f"\n  Products: {ready}/{len(PRODUCT_INFO)} ready")
    print(f"  Total individual value: ${total_value:.2f}")
    print(f"  Bundles: {len(BUNDLES)}")

    for p in catalog["products"]:
        icon = "✅" if p["status"] == "ready" else ("🔧" if "generat" in p["status"] else "🔲")
        print(f"  {icon} [{p['id']}] {p['name']} — ${p['price']} ({p['status']})")

    print("=" * 60)
    return catalog


if __name__ == "__main__":
    generate_catalog()
