"""
SheetCraft AI — Master Product Generator
Generates all product templates in one go.
"""

import importlib.util
import os
import sys
import time


PRODUCTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "products")

PRODUCT_GENERATORS = [
    ("01-monthly-budget-tracker", "generate_template.py"),
    ("02-annual-financial-overview", "generate_template.py"),
    ("03-freelancer-income-tracker", "generate_template.py"),
    ("04-debt-payoff-planner", "generate_template.py"),
    ("05-503020-budget", "generate_template.py"),
    ("06-small-business-pl", "generate_template.py"),
    ("07-inventory-manager", "generate_template.py"),
    ("08-client-crm", "generate_template.py"),
    ("09-habit-tracker", "generate_template.py"),
    ("10-project-management", "generate_template.py"),
]


def load_and_run(product_dir, script_name):
    script_path = os.path.join(PRODUCTS_DIR, product_dir, script_name)
    if not os.path.exists(script_path):
        return None

    spec = importlib.util.spec_from_file_location(f"{product_dir}.generator", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "generate"):
        return module.generate()
    return None


def main():
    print("=" * 60)
    print("  SheetCraft AI — Generating All Products")
    print("=" * 60)

    results = []
    total_start = time.time()

    for product_dir, script_name in PRODUCT_GENERATORS:
        script_path = os.path.join(PRODUCTS_DIR, product_dir, script_name)
        if not os.path.exists(script_path):
            print(f"  SKIP  {product_dir} (generator not found)")
            results.append((product_dir, "skipped"))
            continue

        try:
            start = time.time()
            output = load_and_run(product_dir, script_name)
            elapsed = time.time() - start
            print(f"  OK    {product_dir} ({elapsed:.1f}s)")
            results.append((product_dir, "success"))
        except Exception as e:
            print(f"  FAIL  {product_dir}: {e}")
            results.append((product_dir, f"error: {e}"))

    total_elapsed = time.time() - total_start
    print("=" * 60)

    success = sum(1 for _, s in results if s == "success")
    skipped = sum(1 for _, s in results if s == "skipped")
    failed = sum(1 for _, s in results if s.startswith("error"))

    print(f"  Done: {success} generated, {skipped} skipped, {failed} failed")
    print(f"  Total time: {total_elapsed:.1f}s")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
