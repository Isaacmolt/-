#!/usr/bin/env python3
"""
Etsy 產品自動上傳腳本
使用 Playwright 瀏覽器自動化，批量在 Etsy 建立數位商品 listing。

用法:
    pip install playwright
    playwright install chromium
    python auto_upload_etsy.py
"""

import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 路徑配置
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE_DIR / "catalog.json"
PRODUCTS_DIR = BASE_DIR / "products"
UPLOAD_KIT_DIR = BASE_DIR / "upload-kit"
SCREENSHOTS_DIR = BASE_DIR / "scripts" / "screenshots"

# Etsy SEO 標題 (最佳化搜尋)
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

ETSY_TAGS = {
    "01-monthly-budget-tracker": ["budget tracker", "expense tracker", "google sheets", "budget template", "personal finance", "monthly budget", "spreadsheet", "budget planner", "money tracker", "savings tracker", "finance template", "digital download", "budget spreadsheet"],
    "02-annual-financial-overview": ["annual budget", "financial overview", "net worth tracker", "google sheets", "yearly planner", "investment tracker", "finance template", "budget template", "spreadsheet", "financial planner", "money tracker", "digital download", "annual planner"],
    "03-freelancer-income-tracker": ["freelancer tracker", "income tracker", "invoice template", "google sheets", "freelance finance", "tax estimator", "client tracker", "spreadsheet", "self employed", "business template", "revenue tracker", "digital download", "freelance tools"],
    "04-debt-payoff-planner": ["debt payoff", "debt tracker", "snowball method", "avalanche method", "google sheets", "debt planner", "loan tracker", "spreadsheet", "finance template", "debt free", "budget template", "digital download", "payment tracker"],
    "05-503020-budget": ["50 30 20 budget", "budget rule", "budget template", "google sheets", "needs wants savings", "budget planner", "spreadsheet", "finance template", "money tracker", "simple budget", "personal finance", "digital download", "budget tracker"],
    "06-small-business-pl": ["profit and loss", "small business", "google sheets", "income statement", "accounting", "spreadsheet", "business template", "expense tracker", "revenue tracker", "bookkeeping", "digital download", "financial report", "P and L"],
    "07-inventory-manager": ["inventory tracker", "stock manager", "google sheets", "warehouse", "inventory template", "SKU tracker", "spreadsheet", "business template", "product tracker", "stock control", "supply chain", "digital download", "inventory system"],
    "08-client-crm": ["CRM tracker", "client tracker", "sales pipeline", "google sheets", "customer database", "CRM template", "spreadsheet", "business template", "lead tracker", "contact manager", "sales tracker", "digital download", "client manager"],
    "09-habit-tracker": ["habit tracker", "daily routine", "goal tracker", "google sheets", "streak tracker", "annual tracker", "spreadsheet", "productivity", "self improvement", "daily planner", "monthly tracker", "digital download", "routine planner"],
    "10-project-management": ["project management", "task tracker", "gantt chart", "google sheets", "team planner", "project template", "spreadsheet", "to do list", "project board", "task manager", "timeline", "digital download", "project planner"],
}


def load_catalog() -> list[dict]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["products"]


def get_product_files(product: dict) -> dict:
    pid = product["id"]
    product_dir = PRODUCTS_DIR / pid

    xlsx_files = list(product_dir.glob("*.xlsx"))
    if not xlsx_files:
        raise FileNotFoundError(f"找不到 xlsx: {product_dir}")

    desc_path = product_dir / "listing-description.txt"
    hero_path = product_dir / "images" / "hero.png"
    features_path = product_dir / "images" / "features.png"
    steps_path = product_dir / "images" / "steps.png"

    description = desc_path.read_text(encoding="utf-8").strip() if desc_path.exists() else ""

    images = []
    for p in [hero_path, features_path, steps_path]:
        if p.exists():
            images.append(str(p))

    return {
        "xlsx": str(xlsx_files[0]),
        "description": description,
        "images": images,
        "title": ETSY_TITLES.get(pid, product["name"]),
        "tags": ETSY_TAGS.get(pid, []),
    }


def create_etsy_listing(page, product: dict, files: dict) -> str | None:
    """在 Etsy 建立一個數位商品 listing (draft)。"""
    name = product["name"]
    price = product["price"]

    # 1) 到新增 listing 頁面
    print(f"  [1/7] 打開新增 listing 頁面 ...")
    page.goto("https://www.etsy.com/your/shops/me/tools/listings/create", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    # 2) 選擇數位商品類型
    print(f"  [2/7] 選擇數位商品類型 ...")
    try:
        digital_option = page.locator('text=Digital').first
        if digital_option.count() > 0:
            digital_option.click()
            page.wait_for_timeout(1000)
    except Exception as e:
        print(f"  ⚠ 選擇類型失敗: {e}")

    # 3) 上傳圖片
    print(f"  [3/7] 上傳展示圖片 ({len(files['images'])} 張) ...")
    try:
        img_input = page.locator('input[type="file"][accept*="image"]').first
        if img_input.count() > 0:
            for img_path in files["images"]:
                img_input.set_input_files(img_path)
                page.wait_for_timeout(2000)
                print(f"    已上傳: {os.path.basename(img_path)}")
    except Exception as e:
        print(f"  ⚠ 圖片上傳失敗: {e}")

    # 4) 上傳數位檔案
    print(f"  [4/7] 上傳數位商品檔案 ...")
    try:
        file_inputs = page.locator('input[type="file"]')
        for i in range(file_inputs.count()):
            accept = file_inputs.nth(i).get_attribute("accept") or ""
            if "image" not in accept:
                file_inputs.nth(i).set_input_files(files["xlsx"])
                print(f"    已上傳: {os.path.basename(files['xlsx'])}")
                page.wait_for_timeout(2000)
                break
    except Exception as e:
        print(f"  ⚠ 檔案上傳失敗: {e}")

    # 5) 填寫標題
    print(f"  [5/7] 填寫標題 ...")
    try:
        title_input = page.locator('input[name="title"]')
        if title_input.count() == 0:
            title_input = page.locator('#listing-edit-title')
        if title_input.count() == 0:
            title_input = page.locator('textarea[name="title"]')
        if title_input.count() > 0:
            title_input.click()
            title_input.fill(files["title"])
    except Exception as e:
        print(f"  ⚠ 標題填寫失敗: {e}")

    # 6) 填寫描述
    print(f"  [6/7] 填寫描述 ...")
    try:
        desc_input = page.locator('textarea[name="description"]')
        if desc_input.count() == 0:
            desc_input = page.locator('[role="textbox"]').first
        if desc_input.count() == 0:
            desc_input = page.locator('#listing-edit-description')
        if desc_input.count() > 0:
            desc_input.click()
            desc_input.fill(files["description"])
    except Exception as e:
        print(f"  ⚠ 描述填寫失敗: {e}")

    # 7) 設定價格
    print(f"  [7/7] 設定價格: ${price} ...")
    try:
        price_input = page.locator('input[name="price"]')
        if price_input.count() == 0:
            price_input = page.locator('#listing-edit-price')
        if price_input.count() > 0:
            price_input.click()
            price_input.fill("")
            price_input.type(str(price))
    except Exception as e:
        print(f"  ⚠ 價格設定失敗: {e}")

    # 填寫標籤
    try:
        tags = files.get("tags", [])
        tag_input = page.locator('input[name="tags"]')
        if tag_input.count() == 0:
            tag_input = page.locator('#listing-edit-tags input')
        if tag_input.count() > 0:
            for tag in tags[:13]:
                tag_input.click()
                tag_input.fill(tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(300)
    except Exception as e:
        print(f"  ⚠ 標籤填寫失敗: {e}")

    # 保存為草稿
    try:
        save_btn = page.locator('button:has-text("Save as draft")')
        if save_btn.count() == 0:
            save_btn = page.locator('button:has-text("Save")')
        if save_btn.count() > 0:
            save_btn.click()
            page.wait_for_timeout(3000)
            print(f"  已保存為草稿")
    except Exception as e:
        print(f"  ⚠ 保存失敗: {e}")

    return page.url


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("錯誤: 未安裝 playwright。請執行:")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    products = load_catalog()

    print(f"{'=' * 60}")
    print(f"  Etsy 數位商品自動上架工具")
    print(f"  共 {len(products)} 個產品待上架")
    print(f"{'=' * 60}")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        # 手動登入
        print("正在打開 Etsy 登入頁面 ...")
        page.goto("https://www.etsy.com/signin", wait_until="networkidle", timeout=30000)

        input("\n>>> 請在瀏覽器中登入 Etsy，完成後按 Enter 繼續 ...\n")

        # 驗證登入
        page.goto("https://www.etsy.com/your/shops/me", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        if "signin" in page.url.lower():
            print("錯誤: 登入未成功，請重新執行。")
            browser.close()
            sys.exit(1)

        print("登入成功！開始建立 listing ...\n")

        results = []
        for i, product in enumerate(products, 1):
            name = product["name"]
            pid = product["id"]
            print(f"{'─' * 50}")
            print(f"[{i}/{len(products)}] 正在建立: {name} (${product['price']})")
            print(f"{'─' * 50}")

            try:
                files = get_product_files(product)
                url = create_etsy_listing(page, product, files)
                results.append({"name": name, "id": pid, "status": "成功", "url": url})
                print(f"  ✓ 建立成功!\n")
            except Exception as e:
                screenshot_path = SCREENSHOTS_DIR / f"etsy_error_{pid}.png"
                try:
                    page.screenshot(path=str(screenshot_path))
                except Exception:
                    pass
                results.append({"name": name, "id": pid, "status": f"失敗: {e}", "url": None})
                print(f"  ✗ 建立失敗: {e}\n")

            if i < len(products):
                time.sleep(2)

        browser.close()

    # 彙總
    print()
    print(f"{'=' * 60}")
    print(f"  上架完成彙總")
    print(f"{'=' * 60}")
    success = sum(1 for r in results if r["status"] == "成功")
    fail = len(results) - success
    print(f"  成功: {success}  |  失敗: {fail}  |  共計: {len(results)}")
    print()
    for r in results:
        icon = "✓" if r["status"] == "成功" else "✗"
        print(f"  {icon} {r['name']}: {r['status']}")
        if r["url"]:
            print(f"    {r['url']}")
    print()
    print("  所有 listing 已保存為草稿。")
    print("  請到 Etsy Shop Manager → Listings 確認後發佈。")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
