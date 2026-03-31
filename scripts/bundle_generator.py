"""
SheetCraft AI — Bundle Package Creator
Creates ZIP bundles of multiple products for sale as combo packs.
"""

import os
import zipfile
import glob

PRODUCTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "products")
BUNDLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bundles")

BUNDLE_CONFIGS = {
    "Personal_Finance_Bundle": {
        "name": "Personal Finance Bundle",
        "price": "$19.99",
        "products": [
            "01-monthly-budget-tracker",
            "02-annual-financial-overview",
            "04-debt-payoff-planner",
            "05-503020-budget",
        ],
        "description": "Complete personal finance toolkit — budget tracking, annual overview, debt payoff, and the 50/30/20 method.",
    },
    "Small_Business_Bundle": {
        "name": "Small Business Bundle",
        "price": "$24.99",
        "products": [
            "06-small-business-pl",
            "07-inventory-manager",
            "08-client-crm",
        ],
        "description": "Everything a small business needs — P&L statements, inventory management, and client CRM.",
    },
    "Freelancer_Bundle": {
        "name": "Freelancer Bundle",
        "price": "$14.99",
        "products": [
            "03-freelancer-income-tracker",
            "05-503020-budget",
            "10-project-management",
        ],
        "description": "Built for freelancers — income tracking, budgeting, and project management in one package.",
    },
    "Ultimate_Productivity_Bundle": {
        "name": "Ultimate Productivity Bundle",
        "price": "$39.99",
        "products": [
            "01-monthly-budget-tracker",
            "02-annual-financial-overview",
            "03-freelancer-income-tracker",
            "04-debt-payoff-planner",
            "05-503020-budget",
            "06-small-business-pl",
            "07-inventory-manager",
            "08-client-crm",
            "09-habit-tracker",
            "10-project-management",
        ],
        "description": "Every single template we make — the ultimate toolkit for personal and business productivity.",
    },
}


def find_xlsx_files(product_dir):
    pattern = os.path.join(PRODUCTS_DIR, product_dir, "*.xlsx")
    return glob.glob(pattern)


def create_bundle(bundle_key, config):
    os.makedirs(BUNDLES_DIR, exist_ok=True)

    zip_path = os.path.join(BUNDLES_DIR, f"{bundle_key}_SheetCraft.zip")
    included = []
    missing = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add a README
        readme = f"""SheetCraft AI — {config['name']}

{config['description']}

Included Templates:
"""
        for product_dir in config["products"]:
            xlsx_files = find_xlsx_files(product_dir)
            if xlsx_files:
                for f in xlsx_files:
                    arcname = os.path.basename(f)
                    zf.write(f, arcname)
                    included.append(arcname)
                    readme += f"  - {arcname}\n"
            else:
                missing.append(product_dir)

        readme += """
How to Use:
1. Open each .xlsx file in Google Sheets (File → Import → Upload)
2. Or open directly in Microsoft Excel
3. Each template includes an Instructions tab

Thank you for your purchase!
For support, message us on Etsy.
"""
        zf.writestr("README.txt", readme)

    return zip_path, included, missing


def main():
    print("=" * 60)
    print("  SheetCraft AI — Bundle Generator")
    print("=" * 60)

    for bundle_key, config in BUNDLE_CONFIGS.items():
        zip_path, included, missing = create_bundle(bundle_key, config)
        status = "OK" if not missing else "PARTIAL"
        print(f"  {status}  {config['name']}")
        print(f"         {len(included)} files included, {len(missing)} missing")
        if missing:
            for m in missing:
                print(f"         Missing: {m}")
        print(f"         → {zip_path}")

    print("=" * 60)
    print("  Done!")


if __name__ == "__main__":
    main()
