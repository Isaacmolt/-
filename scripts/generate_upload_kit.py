#!/usr/bin/env python3
"""
SheetCraft AI — Upload Kit Generator
生成每個產品的上架素材包，讓你只需「複製貼上」就能上架 Etsy / Gumroad。

用法：
    python scripts/generate_upload_kit.py

輸出：
    upload-kit/
    ├── 01-monthly-budget-tracker/
    │   ├── Monthly_Budget_Tracker_SheetCraft.xlsx  (複製的產品檔)
    │   ├── hero.png, features.png, steps.png       (展示圖)
    │   ├── TITLE.txt          ← 複製貼上到標題欄
    │   ├── DESCRIPTION.txt    ← 複製貼上到描述欄
    │   ├── TAGS.txt           ← 複製貼上到標籤欄（逗號分隔）
    │   ├── PRICE.txt          ← 填入的價格
    │   └── README-上架步驟.txt ← 中文操作指南
    ├── 02-annual-financial-overview/
    │   └── ...
    └── ...（共 10 個產品 + 4 套裝）
"""

import json
import os
import shutil
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")
PRODUCTS_DIR = os.path.join(BASE_DIR, "products")
BUNDLES_DIR = os.path.join(BASE_DIR, "bundles")
OUTPUT_DIR = os.path.join(BASE_DIR, "upload-kit")

# Etsy SEO titles (optimized for search)
ETSY_TITLES = {
    "01-monthly-budget-tracker": "Monthly Budget Tracker Google Sheets Template | Expense Tracker Spreadsheet | Personal Finance Planner | Instant Download",
    "02-annual-financial-overview": "Annual Financial Overview Google Sheets | Yearly Budget Planner | Net Worth Tracker | Investment Dashboard | Instant Download",
    "03-freelancer-income-tracker": "Freelancer Income Tracker Google Sheets | Invoice Template | Client Manager | Tax Estimator Spreadsheet | Instant Download",
    "04-debt-payoff-planner": "Debt Payoff Planner Google Sheets | Snowball vs Avalanche Calculator | Debt Tracker Spreadsheet | Instant Download",
    "05-503020-budget": "50/30/20 Budget Template Google Sheets | Budget Rule Spreadsheet | Needs Wants Savings Tracker | Instant Download",
    "06-small-business-pl": "Small Business Profit and Loss Google Sheets | P&L Statement Template | Income Expense Tracker | Instant Download",
    "07-inventory-manager": "Inventory Management Google Sheets Template | Stock Tracker | Warehouse Manager | SKU Spreadsheet | Instant Download",
    "08-client-crm": "Client CRM Tracker Google Sheets | Sales Pipeline Template | Customer Database Spreadsheet | Instant Download",
    "09-habit-tracker": "Annual Habit Tracker Google Sheets | Daily Routine Planner | Goal Tracker Spreadsheet | 12 Month Tracker | Instant Download",
    "10-project-management": "Project Management Board Google Sheets | Task Tracker Template | Gantt Chart | Team Planner Spreadsheet | Instant Download",
}

# Etsy tags (max 13 per listing, each max 20 chars)
ETSY_TAGS = {
    "01-monthly-budget-tracker": [
        "budget tracker", "expense tracker", "google sheets", "budget template",
        "personal finance", "monthly budget", "spreadsheet", "budget planner",
        "money tracker", "savings tracker", "finance template", "digital download",
        "budget spreadsheet"
    ],
    "02-annual-financial-overview": [
        "annual budget", "financial overview", "net worth tracker", "google sheets",
        "yearly planner", "investment tracker", "finance template", "budget template",
        "spreadsheet", "financial planner", "money tracker", "digital download",
        "annual planner"
    ],
    "03-freelancer-income-tracker": [
        "freelancer tracker", "income tracker", "invoice template", "google sheets",
        "freelance finance", "tax estimator", "client tracker", "spreadsheet",
        "self employed", "business template", "revenue tracker", "digital download",
        "freelance tools"
    ],
    "04-debt-payoff-planner": [
        "debt payoff", "debt tracker", "snowball method", "avalanche method",
        "google sheets", "debt planner", "loan tracker", "spreadsheet",
        "finance template", "debt free", "budget template", "digital download",
        "payment tracker"
    ],
    "05-503020-budget": [
        "50 30 20 budget", "budget rule", "budget template", "google sheets",
        "needs wants savings", "budget planner", "spreadsheet", "finance template",
        "money tracker", "simple budget", "personal finance", "digital download",
        "budget tracker"
    ],
    "06-small-business-pl": [
        "profit and loss", "P&L statement", "small business", "google sheets",
        "income statement", "accounting", "spreadsheet", "business template",
        "expense tracker", "revenue tracker", "bookkeeping", "digital download",
        "financial report"
    ],
    "07-inventory-manager": [
        "inventory tracker", "stock manager", "google sheets", "warehouse",
        "inventory template", "SKU tracker", "spreadsheet", "business template",
        "product tracker", "stock control", "supply chain", "digital download",
        "inventory system"
    ],
    "08-client-crm": [
        "CRM tracker", "client tracker", "sales pipeline", "google sheets",
        "customer database", "CRM template", "spreadsheet", "business template",
        "lead tracker", "contact manager", "sales tracker", "digital download",
        "client manager"
    ],
    "09-habit-tracker": [
        "habit tracker", "daily routine", "goal tracker", "google sheets",
        "streak tracker", "annual tracker", "spreadsheet", "productivity",
        "self improvement", "daily planner", "monthly tracker", "digital download",
        "routine planner"
    ],
    "10-project-management": [
        "project management", "task tracker", "gantt chart", "google sheets",
        "team planner", "project template", "spreadsheet", "to do list",
        "project board", "task manager", "timeline", "digital download",
        "project planner"
    ],
}


def generate_upload_kit():
    """Generate the upload kit for all products and bundles."""
    # Clean and create output dir
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Load catalog
    with open(CATALOG_PATH, "r") as f:
        catalog = json.load(f)

    print("=" * 60)
    print("  SheetCraft AI — Upload Kit Generator")
    print("=" * 60)
    print()

    # Process each product
    for product in catalog["products"]:
        pid = product["id"]
        name = product["name"]
        price = product["price"]
        product_dir = os.path.join(PRODUCTS_DIR, pid)
        kit_dir = os.path.join(OUTPUT_DIR, pid)
        os.makedirs(kit_dir, exist_ok=True)

        print(f"  📦 {name}")

        # 1. Copy .xlsx file
        for xlsx_file in product["files"]:
            src = os.path.join(product_dir, xlsx_file)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(kit_dir, xlsx_file))
                print(f"     ✓ {xlsx_file}")

        # 2. Copy images
        images_dir = os.path.join(product_dir, "images")
        if os.path.exists(images_dir):
            for img in ["hero.png", "features.png", "steps.png"]:
                src = os.path.join(images_dir, img)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(kit_dir, img))
            print("     ✓ 3 images (hero, features, steps)")

        # 3. TITLE.txt
        title = ETSY_TITLES.get(pid, name)
        with open(os.path.join(kit_dir, "TITLE.txt"), "w") as f:
            f.write(title)
        print("     ✓ TITLE.txt")

        # 4. DESCRIPTION.txt (from listing-description.txt)
        desc_src = os.path.join(product_dir, "listing-description.txt")
        if os.path.exists(desc_src):
            shutil.copy2(desc_src, os.path.join(kit_dir, "DESCRIPTION.txt"))
        print("     ✓ DESCRIPTION.txt")

        # 5. TAGS.txt
        tags = ETSY_TAGS.get(pid, product.get("tags", []))
        with open(os.path.join(kit_dir, "TAGS.txt"), "w") as f:
            f.write(", ".join(tags))
        print("     ✓ TAGS.txt")

        # 6. PRICE.txt
        with open(os.path.join(kit_dir, "PRICE.txt"), "w") as f:
            f.write(f"${price:.2f} USD\n\nEtsy: ${price:.2f}\nGumroad: ${price:.2f}")
        print("     ✓ PRICE.txt")

        # 7. README - 上架步驟
        readme = f"""╔══════════════════════════════════════════════════╗
║  {name}  —  上架步驟
╚══════════════════════════════════════════════════╝

價格：${price:.2f} USD

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【Etsy 上架步驟】

1. 登入 Etsy → Shop Manager → Listings → Add a listing
2. 類型選「Digital」(數位商品)
3. 標題：打開 TITLE.txt，全選複製，貼到標題欄
4. 描述：打開 DESCRIPTION.txt，全選複製，貼到描述欄
5. 圖片：依序上傳 hero.png → features.png → steps.png
6. 檔案：上傳 {product["files"][0]}
7. 價格：填入 ${price:.2f}
8. 標籤：打開 TAGS.txt，把每個標籤分別填入（Etsy 最多 13 個）
9. Category 選：Templates → Spreadsheets
10. 點 Publish！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【Gumroad 上架步驟】

1. 登入 Gumroad → Dashboard → New Product
2. 名稱：打開 TITLE.txt 複製前半段（產品名稱即可）
3. 描述：打開 DESCRIPTION.txt，全選複製貼上
4. 價格：填入 ${price:.2f}
5. 封面圖：上傳 hero.png
6. 檔案：上傳 {product["files"][0]}
7. 點 Publish！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

這個資料夾裡的所有檔案：
  • {product["files"][0]}  → 數位商品檔案（上傳）
  • hero.png              → 主圖（第一張展示圖）
  • features.png          → 功能介紹圖（第二張）
  • steps.png             → 使用步驟圖（第三張）
  • TITLE.txt             → 標題（複製貼上）
  • DESCRIPTION.txt       → 描述（複製貼上）
  • TAGS.txt              → 標籤（複製貼上）
  • PRICE.txt             → 價格參考
"""
        with open(os.path.join(kit_dir, "README-上架步驟.txt"), "w") as f:
            f.write(readme)
        print("     ✓ README-上架步驟.txt")
        print()

    # Process bundles
    print("  📦 Bundles:")
    for bundle in catalog["bundles"]:
        bid = bundle["id"]
        bname = bundle["name"]
        bprice = bundle["price"]
        kit_dir = os.path.join(OUTPUT_DIR, f"bundle-{bid}")
        os.makedirs(kit_dir, exist_ok=True)

        # Copy ZIP
        zip_path = os.path.join(BUNDLES_DIR, f"{bid}.zip")
        if os.path.exists(zip_path):
            shutil.copy2(zip_path, os.path.join(kit_dir, f"{bid}.zip"))

        # Title
        with open(os.path.join(kit_dir, "TITLE.txt"), "w") as f:
            f.write(f"{bname} | Google Sheets Templates Bundle | Multiple Spreadsheets | Instant Download")

        # Price
        with open(os.path.join(kit_dir, "PRICE.txt"), "w") as f:
            f.write(f"${bprice:.2f} USD")

        # Description
        desc = f"""{bname} — Save big with this value bundle!

Get multiple premium Google Sheets templates at a discounted bundle price.

━━━━━━━━━━━━━━━━━━━━━━━━

WHAT'S INCLUDED:

This bundle contains multiple professionally designed Google Sheets templates, each with:
✔ Automatic calculations and formulas
✔ Beautiful dashboard with visual charts
✔ Step-by-step instructions included
✔ Works on desktop and mobile
✔ Fully customizable

━━━━━━━━━━━━━━━━━━━━━━━━

HOW IT WORKS:

1. Purchase and download the ZIP file
2. Extract the files
3. Open each template in Google Sheets (File → Make a Copy)
4. Start using immediately!

━━━━━━━━━━━━━━━━━━━━━━━━

Bundle Price: ${bprice:.2f} (Save up to 45%!)

INSTANT DOWNLOAD — Start now!
"""
        with open(os.path.join(kit_dir, "DESCRIPTION.txt"), "w") as f:
            f.write(desc)

        # Tags
        with open(os.path.join(kit_dir, "TAGS.txt"), "w") as f:
            f.write("google sheets bundle, spreadsheet bundle, template bundle, budget tracker, finance template, business template, digital download, instant download, spreadsheet pack, planner bundle, productivity bundle, template pack, google sheets")

        readme = f"""╔══════════════════════════════════════════════════╗
║  {bname}  —  上架步驟
╚══════════════════════════════════════════════════╝

價格：${bprice:.2f} USD

上架方式與單品相同：
1. 標題 → 複製 TITLE.txt
2. 描述 → 複製 DESCRIPTION.txt
3. 檔案 → 上傳 {bid}.zip
4. 價格 → ${bprice:.2f}
5. 標籤 → 複製 TAGS.txt
"""
        with open(os.path.join(kit_dir, "README-上架步驟.txt"), "w") as f:
            f.write(readme)

        print(f"     ✓ {bname} (${bprice:.2f})")

    print()
    print("=" * 60)
    total = len(catalog["products"]) + len(catalog["bundles"])
    print(f"  Done! {total} upload kits generated in upload-kit/")
    print()
    print("  下一步：")
    print("  1. 打開 upload-kit/ 資料夾")
    print("  2. 每個子資料夾就是一個產品")
    print("  3. 照 README-上架步驟.txt 的指示複製貼上即可")
    print("=" * 60)


if __name__ == "__main__":
    generate_upload_kit()
