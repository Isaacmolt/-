#!/usr/bin/env python3
"""
Gumroad 产品自动上传脚本
使用 Playwright 浏览器自动化，批量创建 Gumroad 产品。

用法:
    pip install playwright
    playwright install chromium
    python auto_upload_gumroad.py
"""

import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # /home/user/-
CATALOG_PATH = BASE_DIR / "catalog.json"
PRODUCTS_DIR = BASE_DIR / "products"
SCREENSHOTS_DIR = BASE_DIR / "scripts" / "screenshots"
STORE_URL = "https://8380185741749.gumroad.com"

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def load_catalog() -> list[dict]:
    """读取 catalog.json 并返回产品列表。"""
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["products"]


def get_product_files(product: dict) -> dict:
    """定位某个产品的全部本地文件。"""
    pid = product["id"]
    product_dir = PRODUCTS_DIR / pid

    # xlsx 文件
    xlsx_files = list(product_dir.glob("*.xlsx"))
    if not xlsx_files:
        raise FileNotFoundError(f"找不到 xlsx 文件: {product_dir}")
    xlsx_path = xlsx_files[0]

    # 描述文本
    desc_path = product_dir / "listing-description.txt"
    if not desc_path.exists():
        raise FileNotFoundError(f"找不到描述文件: {desc_path}")

    # 预览图
    hero_path = product_dir / "images" / "hero.png"
    if not hero_path.exists():
        raise FileNotFoundError(f"找不到预览图: {hero_path}")

    description = desc_path.read_text(encoding="utf-8").strip()

    return {
        "xlsx": str(xlsx_path),
        "hero": str(hero_path),
        "description": description,
    }


# ---------------------------------------------------------------------------
# 核心上传逻辑
# ---------------------------------------------------------------------------

def create_product(page, product: dict, files: dict) -> str | None:
    """
    在 Gumroad 上创建单个产品（保存为草稿）。
    返回产品编辑页 URL，失败返回 None。
    """
    name = product["name"]
    price = product["price"]

    # 1) 进入新建产品页面
    print(f"  [1/6] 打开产品创建页面 ...")
    page.goto("https://app.gumroad.com/products/new", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # 2) 填写产品名称
    print(f"  [2/6] 填写产品名称: {name}")
    name_input = page.locator('input[placeholder="Name of product"]')
    if name_input.count() == 0:
        # 备用选择器
        name_input = page.locator('input[name="name"]')
    if name_input.count() == 0:
        name_input = page.locator('[data-testid="product-name-input"]')
    if name_input.count() == 0:
        # 尝试获取第一个可见的文本输入
        name_input = page.locator('input[type="text"]').first
    name_input.click()
    name_input.fill(name)

    # 3) 设置价格
    print(f"  [3/6] 设置价格: ${price}")
    price_input = page.locator('input[name="price"]')
    if price_input.count() == 0:
        price_input = page.locator('input[placeholder*="rice"]')
    if price_input.count() == 0:
        # 查找包含 $ 附近的 input
        price_input = page.locator('input[type="text"]').nth(1)
    price_input.click()
    price_input.fill("")
    price_input.type(str(price))

    # 4) 点击创建 / 初始保存 —— Gumroad 通常有 "Add product" 按钮
    print(f"  [4/6] 点击创建产品按钮 ...")
    create_btn = page.locator('button:has-text("Add product")')
    if create_btn.count() == 0:
        create_btn = page.locator('button:has-text("Create product")')
    if create_btn.count() == 0:
        create_btn = page.locator('button[type="submit"]').first
    create_btn.click()
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle", timeout=15000)

    product_url = page.url
    print(f"  产品页面: {product_url}")

    # 5) 填写描述 —— 产品创建后进入编辑页面
    print(f"  [5/6] 填写产品描述 ...")
    try:
        # Gumroad 使用富文本编辑器，尝试多种选择器
        desc_editor = page.locator('[role="textbox"]').first
        if desc_editor.count() == 0:
            desc_editor = page.locator('.trix-content').first
        if desc_editor.count() == 0:
            desc_editor = page.locator('textarea').first
        if desc_editor.count() == 0:
            desc_editor = page.locator('[contenteditable="true"]').first

        if desc_editor.count() > 0:
            desc_editor.click()
            # 粘贴描述文本（比逐字打出快得多）
            page.keyboard.press("Control+A")
            page.keyboard.press("Delete")
            desc_editor.fill(files["description"])
        else:
            print("  ⚠ 未找到描述编辑框，跳过描述填写")
    except Exception as e:
        print(f"  ⚠ 描述填写失败: {e}")

    # 6) 上传文件
    print(f"  [6/6] 上传产品文件 ...")
    try:
        # 上传 xlsx 产品文件
        upload_input = page.locator('input[type="file"]').first
        if upload_input.count() > 0:
            upload_input.set_input_files(files["xlsx"])
            print(f"  已上传: {os.path.basename(files['xlsx'])}")
            page.wait_for_timeout(3000)
        else:
            print("  ⚠ 未找到文件上传控件")
    except Exception as e:
        print(f"  ⚠ 产品文件上传失败: {e}")

    # 上传预览图 (hero.png)
    try:
        # 预览图通常是第二个 file input 或有特定属性
        file_inputs = page.locator('input[type="file"]')
        input_count = file_inputs.count()
        if input_count >= 2:
            file_inputs.nth(1).set_input_files(files["hero"])
            print(f"  已上传预览图: hero.png")
            page.wait_for_timeout(2000)
        elif input_count == 1:
            # 可能只有一个，尝试用第一个上传图片
            print("  ⚠ 仅找到一个上传控件，尝试上传预览图 ...")
            file_inputs.first.set_input_files(files["hero"])
            page.wait_for_timeout(2000)
        else:
            print("  ⚠ 未找到预览图上传控件")
    except Exception as e:
        print(f"  ⚠ 预览图上传失败: {e}")

    # 保存 —— 查找并点击保存按钮
    try:
        save_btn = page.locator('button:has-text("Save")').first
        if save_btn.count() == 0:
            save_btn = page.locator('button:has-text("Publish")').first
        if save_btn.count() > 0:
            save_btn.click()
            page.wait_for_timeout(2000)
            print(f"  已保存")
    except Exception as e:
        print(f"  ⚠ 保存失败: {e}")

    return product_url


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("错误: 未安装 playwright。请运行:")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    # 创建截图目录
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # 加载产品目录
    products = load_catalog()
    print(f"=" * 60)
    print(f"  Gumroad 产品自动上传工具")
    print(f"  共 {len(products)} 个产品待创建")
    print(f"  商店地址: {STORE_URL}")
    print(f"=" * 60)
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        # ---- 手动登录 ----
        print("正在打开 Gumroad 登录页面 ...")
        page.goto("https://gumroad.com/login", wait_until="networkidle", timeout=30000)

        input("\n>>> 请在浏览器窗口中登录 Gumroad，完成后按 Enter 继续 ...\n")

        # 验证登录 —— 尝试访问仪表盘
        page.goto("https://app.gumroad.com/dashboard", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        if "login" in page.url.lower():
            print("错误: 登录似乎未成功，请重新运行脚本。")
            browser.close()
            sys.exit(1)

        print("登录成功！开始创建产品 ...\n")

        # ---- 逐个创建产品 ----
        results: list[dict] = []

        for i, product in enumerate(products, 1):
            name = product["name"]
            pid = product["id"]
            print(f"{'─' * 50}")
            print(f"[{i}/{len(products)}] 正在创建: {name} (${product['price']})")
            print(f"{'─' * 50}")

            try:
                files = get_product_files(product)
                url = create_product(page, product, files)
                results.append({
                    "name": name,
                    "id": pid,
                    "status": "成功",
                    "url": url or "未知",
                })
                print(f"  ✓ 创建成功!\n")

            except Exception as e:
                # 截图用于调试
                screenshot_path = SCREENSHOTS_DIR / f"error_{pid}.png"
                try:
                    page.screenshot(path=str(screenshot_path))
                    print(f"  已保存错误截图: {screenshot_path}")
                except Exception:
                    pass

                results.append({
                    "name": name,
                    "id": pid,
                    "status": f"失败: {e}",
                    "url": None,
                })
                print(f"  ✗ 创建失败: {e}\n")

            # 产品之间等待 2 秒
            if i < len(products):
                time.sleep(2)

        browser.close()

    # ---- 打印汇总 ----
    print()
    print(f"{'=' * 60}")
    print(f"  上传完成汇总")
    print(f"{'=' * 60}")
    success_count = sum(1 for r in results if r["status"] == "成功")
    fail_count = len(results) - success_count
    print(f"  成功: {success_count}  |  失败: {fail_count}  |  共计: {len(results)}")
    print()

    for r in results:
        status_icon = "✓" if r["status"] == "成功" else "✗"
        url_str = r["url"] or "N/A"
        print(f"  {status_icon} {r['name']}")
        print(f"    状态: {r['status']}")
        print(f"    链接: {url_str}")
        print()

    print(f"{'─' * 60}")
    print(f"  Gumroad 商店地址: {STORE_URL}")
    print(f"  产品管理页面:   https://app.gumroad.com/products")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
