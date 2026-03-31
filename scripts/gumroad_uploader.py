#!/usr/bin/env python3
"""
Gumroad Product Uploader — SheetCraft AI
==========================================
Creates products on Gumroad using their API, reading product data from
catalog.json and listing-description.txt.

Usage:
    python gumroad_uploader.py                   # Upload all products
    python gumroad_uploader.py --product 01      # Upload a single product
    python gumroad_uploader.py --dry-run         # Preview without calling API

Environment variables (or .env):
    GUMROAD_ACCESS_TOKEN — Your Gumroad API access token
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_FILE = PROJECT_ROOT / "catalog.json"
PRODUCTS_DIR = PROJECT_ROOT / "products"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GUMROAD_API_BASE = "https://api.gumroad.com/v2"
MAX_RETRIES = 3
RETRY_BACKOFF = 2


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------
def _load_env():
    """Load .env file into os.environ if it exists."""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key not in os.environ:
                    os.environ[key] = value


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"Error: {name} is not set. Check your .env or environment.")
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------
class GumroadClient:
    """Wrapper around the Gumroad API with retry logic."""

    def __init__(self, access_token: str):
        self.access_token = access_token

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{GUMROAD_API_BASE}{path}"
        last_exc = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.request(method, url, timeout=60, **kwargs)

                if resp.status_code == 429:
                    wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                    print(f"  [WARN] Rate limited. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                    print(f"  [WARN] Server error {resp.status_code}. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                return resp

            except requests.exceptions.ConnectionError as e:
                last_exc = e
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                print(f"  [WARN] Connection error. Retrying in {wait}s...")
                time.sleep(wait)
            except requests.exceptions.Timeout as e:
                last_exc = e
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                print(f"  [WARN] Timeout. Retrying in {wait}s...")
                time.sleep(wait)

        if last_exc:
            raise last_exc
        raise RuntimeError(f"API request failed after {MAX_RETRIES} attempts.")

    def create_product(self, name: str, description: str, price: float,
                       tags: list[str], file_path: Optional[Path] = None,
                       preview_image: Optional[Path] = None) -> dict:
        """
        Create a product on Gumroad.
        Price is in USD (e.g., 5.99 -> 599 cents).
        """
        data = {
            "access_token": self.access_token,
            "name": name,
            "description": description,
            "price": int(price * 100),  # Gumroad uses cents
            "tags[]": tags,
            "published": "false",  # Create as unpublished for review
        }

        files = {}
        if file_path and file_path.exists():
            files["file"] = (
                file_path.name,
                open(file_path, "rb"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        if preview_image and preview_image.exists():
            files["preview"] = (
                preview_image.name,
                open(preview_image, "rb"),
                "image/png",
            )

        try:
            resp = self._request("POST", "/products", data=data, files=files if files else None)
        finally:
            # Close any opened file handles
            for key in files:
                try:
                    files[key][1].close()
                except Exception:
                    pass

        return resp.json()


# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------
def load_catalog() -> dict:
    if not CATALOG_FILE.exists():
        print(f"Error: {CATALOG_FILE} not found.")
        sys.exit(1)
    return json.loads(CATALOG_FILE.read_text())


def get_product_description(product_id: str) -> str:
    desc_file = PRODUCTS_DIR / product_id / "listing-description.txt"
    if desc_file.exists():
        return desc_file.read_text().strip()
    print(f"  [WARN] No listing-description.txt for {product_id}")
    return ""


def find_xlsx(product_id: str, file_names: list[str]) -> Optional[Path]:
    """Return the first xlsx file found for this product."""
    product_dir = PRODUCTS_DIR / product_id
    for fn in file_names:
        fp = product_dir / fn
        if fp.exists():
            return fp
    return None


def find_preview_image(product_id: str) -> Optional[Path]:
    """Find a preview/cover image for the product."""
    img_dir = PRODUCTS_DIR / product_id / "images"
    if not img_dir.exists():
        return None
    exts = {".png", ".jpg", ".jpeg"}
    images = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in exts)
    return images[0] if images else None


# ---------------------------------------------------------------------------
# Upload logic
# ---------------------------------------------------------------------------
def upload_product(client: GumroadClient, product: dict, dry_run: bool = False) -> Optional[str]:
    """
    Upload a single product to Gumroad.
    Returns the product ID on success, None on failure.
    """
    pid = product["id"]
    name = product["name"]
    price = product["price"]
    tags = product.get("tags", [])

    print(f"\n{'='*60}")
    print(f"Product: {name} ({pid})")
    print(f"{'='*60}")

    description = get_product_description(pid)
    xlsx = find_xlsx(pid, product.get("files", []))
    preview = find_preview_image(pid)

    print(f"  Name:        {name}")
    print(f"  Price:       ${price}")
    print(f"  Tags:        {len(tags)} tags")
    print(f"  Description: {len(description)} chars")
    print(f"  XLSX:        {xlsx.name if xlsx else 'NOT FOUND'}")
    print(f"  Preview:     {preview.name if preview else 'none'}")

    if dry_run:
        print("  [DRY RUN] Skipping API calls.")
        return None

    try:
        print("  Creating product on Gumroad...")
        result = client.create_product(
            name=name,
            description=description,
            price=price,
            tags=tags,
            file_path=xlsx,
            preview_image=preview,
        )

        if result.get("success"):
            gumroad_id = result["product"]["id"]
            url = result["product"].get("short_url", "")
            print(f"  [OK] Product created: {gumroad_id}")
            if url:
                print(f"  [OK] URL: {url}")
            return gumroad_id
        else:
            error = result.get("message", "Unknown error")
            print(f"  [ERROR] Gumroad API error: {error}")
            return None

    except Exception as e:
        print(f"  [ERROR] Failed to create product: {e}")
        return None
    finally:
        time.sleep(0.5)  # Respect rate limits


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    _load_env()

    access_token = _require_env("GUMROAD_ACCESS_TOKEN")

    dry_run = "--dry-run" in sys.argv
    product_filter = None
    if "--product" in sys.argv:
        idx = sys.argv.index("--product")
        if idx + 1 < len(sys.argv):
            product_filter = sys.argv[idx + 1]

    client = GumroadClient(access_token)
    catalog = load_catalog()
    products = catalog.get("products", [])

    if product_filter:
        products = [p for p in products if p["id"].startswith(product_filter)]
        if not products:
            print(f"No products matching filter '{product_filter}'.")
            sys.exit(1)

    print(f"\nSheetCraft AI — Gumroad Uploader")
    print(f"Products to upload: {len(products)}")
    if dry_run:
        print("[DRY RUN MODE — no API calls will be made]\n")

    results = {}
    for product in products:
        gumroad_id = upload_product(client, product, dry_run=dry_run)
        results[product["id"]] = gumroad_id

    # Summary
    print(f"\n{'='*60}")
    print("UPLOAD SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for v in results.values() if v is not None)
    failed = sum(1 for v in results.values() if v is None)
    for pid, gid in results.items():
        status = f"product {gid}" if gid else ("skipped (dry run)" if dry_run else "FAILED")
        print(f"  {pid}: {status}")
    if not dry_run:
        print(f"\nTotal: {success} succeeded, {failed} failed out of {len(results)}")
    print("\nAll products are created as UNPUBLISHED. Review them on Gumroad before publishing.")


if __name__ == "__main__":
    main()
