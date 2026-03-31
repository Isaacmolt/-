#!/usr/bin/env python3
"""
Etsy Listing Uploader — SheetCraft AI
=======================================
Reads catalog.json, product descriptions, and README tags, then creates
draft listings on Etsy with digital download files and showcase images
via the Etsy Open API v3.

Usage:
    python etsy_uploader.py                   # Upload all products
    python etsy_uploader.py --product 01      # Upload a single product (by prefix)
    python etsy_uploader.py --dry-run         # Preview without calling API

Environment variables (or .env):
    ETSY_API_KEY        — Etsy API keystring
    ETSY_ACCESS_TOKEN   — OAuth 2.0 access token
    ETSY_REFRESH_TOKEN  — OAuth 2.0 refresh token (for auto-refresh)
    ETSY_SHOP_ID        — Your Etsy shop numeric ID
"""

import json
import os
import re
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
ETSY_API_BASE = "https://openapi.etsy.com"
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, doubled each retry
ETSY_TAXONOMY_ID = 7631  # "Digital Downloads > Spreadsheets" — adjust as needed
ETSY_WHO_MADE = "i_did"
ETSY_WHEN_MADE = "2020_2025"
ETSY_IS_SUPPLY = False
ETSY_SHIPPING_PROFILE_ID = None  # Not required for digital-only listings


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
# API helper with retry + token refresh
# ---------------------------------------------------------------------------
class EtsyClient:
    """Thin wrapper around Etsy Open API v3 with retry and token refresh."""

    def __init__(self, api_key: str, access_token: str, refresh_token: str, shop_id: str):
        self.api_key = api_key
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.shop_id = shop_id

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
        }

    def _refresh_token(self):
        """Attempt to refresh the access token."""
        from etsy_auth import refresh_access_token

        tokens = refresh_access_token(self.api_key, self.refresh_token)
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        # Persist refreshed tokens
        _update_env_token(tokens["access_token"], tokens["refresh_token"])

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Execute an API request with retry and automatic token refresh."""
        url = f"{ETSY_API_BASE}{path}"
        last_exc = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.request(
                    method, url, headers=self._headers, timeout=60, **kwargs
                )

                # 401 → try refreshing token once
                if resp.status_code == 401 and attempt == 1:
                    print("  [WARN] 401 Unauthorized — refreshing token...")
                    self._refresh_token()
                    continue

                # 429 → rate limited
                if resp.status_code == 429:
                    wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                    print(f"  [WARN] Rate limited. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    continue

                # 5xx → server error, retry
                if resp.status_code >= 500:
                    wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                    print(f"  [WARN] Server error {resp.status_code}. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp

            except requests.exceptions.ConnectionError as e:
                last_exc = e
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                print(f"  [WARN] Connection error. Retrying in {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            except requests.exceptions.Timeout as e:
                last_exc = e
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                print(f"  [WARN] Timeout. Retrying in {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)

        # Exhausted retries
        if last_exc:
            raise last_exc
        raise RuntimeError(f"API request failed after {MAX_RETRIES} attempts: {method} {path}")

    # ----- Listing endpoints -----

    def create_listing(self, title: str, description: str, price: float, tags: list[str],
                       taxonomy_id: int = ETSY_TAXONOMY_ID) -> dict:
        """Create a draft digital listing."""
        path = f"/v3/application/shops/{self.shop_id}/listings"
        payload = {
            "title": title[:140],  # Etsy max 140 chars
            "description": description,
            "price": price,
            "quantity": 999,  # Digital items: effectively unlimited
            "taxonomy_id": taxonomy_id,
            "who_made": ETSY_WHO_MADE,
            "when_made": ETSY_WHEN_MADE,
            "is_supply": ETSY_IS_SUPPLY,
            "type": "download",  # Digital listing
            "state": "draft",
            "tags": tags[:13],  # Etsy max 13 tags
        }
        if ETSY_SHIPPING_PROFILE_ID:
            payload["shipping_profile_id"] = ETSY_SHIPPING_PROFILE_ID

        resp = self._request("POST", path, json=payload)
        return resp.json()

    def upload_image(self, listing_id: int, image_path: Path, rank: int = 1) -> dict:
        """Upload a listing image."""
        path = f"/v3/application/shops/{self.shop_id}/listings/{listing_id}/images"
        with open(image_path, "rb") as f:
            files = {"image": (image_path.name, f, "image/png")}
            data = {"rank": rank}
            resp = self._request("POST", path, files=files, data=data)
        return resp.json()

    def upload_digital_file(self, listing_id: int, file_path: Path) -> dict:
        """Upload a digital download file to an existing listing."""
        path = f"/v3/application/shops/{self.shop_id}/listings/{listing_id}/files"
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f,
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            resp = self._request("POST", path, files=files)
        return resp.json()


# ---------------------------------------------------------------------------
# Catalog / product helpers
# ---------------------------------------------------------------------------
def load_catalog() -> dict:
    """Load catalog.json."""
    if not CATALOG_FILE.exists():
        print(f"Error: {CATALOG_FILE} not found.")
        sys.exit(1)
    return json.loads(CATALOG_FILE.read_text())


def get_product_description(product_id: str) -> str:
    """Read listing-description.txt for a product."""
    desc_file = PRODUCTS_DIR / product_id / "listing-description.txt"
    if desc_file.exists():
        return desc_file.read_text().strip()
    print(f"  [WARN] No listing-description.txt for {product_id}")
    return ""


def extract_tags_from_readme(product_id: str) -> list[str]:
    """Extract tags from the README.md Etsy tag section."""
    readme = PRODUCTS_DIR / product_id / "README.md"
    if not readme.exists():
        return []

    content = readme.read_text()
    tags = []

    # Look for numbered tag list under a "tags" heading
    tag_section = False
    for line in content.splitlines():
        if re.search(r"標籤|tags", line, re.IGNORECASE):
            tag_section = True
            continue
        if tag_section:
            # Match numbered items like "1. budget spreadsheet"
            m = re.match(r"^\d+\.\s+(.+)", line.strip())
            if m:
                tags.append(m.group(1).strip())
            elif line.strip() == "" and tags:
                break  # End of tag section
            elif line.startswith("#") or line.startswith("**"):
                break  # Next section

    return tags[:13]  # Etsy max 13 tags


def extract_title_from_readme(product_id: str) -> Optional[str]:
    """Extract Etsy-optimized title from README.md if available."""
    readme = PRODUCTS_DIR / product_id / "README.md"
    if not readme.exists():
        return None

    content = readme.read_text()
    title_section = False
    for line in content.splitlines():
        if re.search(r"標題|title", line, re.IGNORECASE) and ":" not in line:
            title_section = True
            continue
        if title_section:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
                return stripped[:140]
    return None


def find_images(product_id: str) -> list[Path]:
    """Find showcase images in the product's images/ directory."""
    img_dir = PRODUCTS_DIR / product_id / "images"
    if not img_dir.exists():
        return []
    exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    images = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in exts)
    return images[:10]  # Etsy max 10 images


def find_xlsx(product_id: str, file_names: list[str]) -> list[Path]:
    """Locate the xlsx files listed in catalog.json for a product."""
    product_dir = PRODUCTS_DIR / product_id
    found = []
    for fn in file_names:
        fp = product_dir / fn
        if fp.exists():
            found.append(fp)
        else:
            print(f"  [WARN] File not found: {fp}")
    return found


# ---------------------------------------------------------------------------
# .env update helper
# ---------------------------------------------------------------------------
def _update_env_token(access_token: str, refresh_token: str):
    """Update tokens in .env after a refresh."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    lines = env_file.read_text().splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("ETSY_ACCESS_TOKEN="):
            new_lines.append(f"ETSY_ACCESS_TOKEN={access_token}")
        elif line.startswith("ETSY_REFRESH_TOKEN="):
            new_lines.append(f"ETSY_REFRESH_TOKEN={refresh_token}")
        else:
            new_lines.append(line)
    env_file.write_text("\n".join(new_lines) + "\n")


# ---------------------------------------------------------------------------
# Upload logic
# ---------------------------------------------------------------------------
def upload_product(client: EtsyClient, product: dict, dry_run: bool = False) -> Optional[int]:
    """
    Upload a single product as an Etsy draft listing.
    Returns the listing_id on success, None on failure.
    """
    pid = product["id"]
    name = product["name"]
    price = product["price"]
    catalog_tags = product.get("tags", [])

    print(f"\n{'='*60}")
    print(f"Product: {name} ({pid})")
    print(f"{'='*60}")

    # Gather data
    description = get_product_description(pid)
    readme_tags = extract_tags_from_readme(pid)
    etsy_title = extract_title_from_readme(pid) or name
    tags = readme_tags if readme_tags else catalog_tags
    xlsx_files = find_xlsx(pid, product.get("files", []))
    images = find_images(pid)

    print(f"  Title:       {etsy_title}")
    print(f"  Price:       ${price}")
    print(f"  Tags:        {len(tags)} tags")
    print(f"  Description: {len(description)} chars")
    print(f"  XLSX files:  {len(xlsx_files)}")
    print(f"  Images:      {len(images)}")

    if dry_run:
        print("  [DRY RUN] Skipping API calls.")
        return None

    # 1. Create draft listing
    try:
        print("  Creating draft listing...")
        listing = client.create_listing(
            title=etsy_title,
            description=description,
            price=price,
            tags=tags,
        )
        listing_id = listing["listing_id"]
        print(f"  [OK] Listing created: ID {listing_id} (draft)")
    except Exception as e:
        print(f"  [ERROR] Failed to create listing: {e}")
        return None

    # 2. Upload digital files
    for fp in xlsx_files:
        try:
            print(f"  Uploading digital file: {fp.name}...")
            client.upload_digital_file(listing_id, fp)
            print(f"  [OK] Digital file uploaded: {fp.name}")
        except Exception as e:
            print(f"  [ERROR] Failed to upload {fp.name}: {e}")

    # 3. Upload images
    for rank, img in enumerate(images, start=1):
        try:
            print(f"  Uploading image ({rank}/{len(images)}): {img.name}...")
            client.upload_image(listing_id, img, rank=rank)
            print(f"  [OK] Image uploaded: {img.name}")
        except Exception as e:
            print(f"  [ERROR] Failed to upload image {img.name}: {e}")

    # Brief pause between products to respect rate limits
    time.sleep(0.5)
    return listing_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    _load_env()

    api_key = _require_env("ETSY_API_KEY")
    access_token = _require_env("ETSY_ACCESS_TOKEN")
    refresh_token = os.environ.get("ETSY_REFRESH_TOKEN", "")
    shop_id = _require_env("ETSY_SHOP_ID")

    dry_run = "--dry-run" in sys.argv
    product_filter = None
    if "--product" in sys.argv:
        idx = sys.argv.index("--product")
        if idx + 1 < len(sys.argv):
            product_filter = sys.argv[idx + 1]

    client = EtsyClient(api_key, access_token, refresh_token, shop_id)
    catalog = load_catalog()
    products = catalog.get("products", [])

    if product_filter:
        products = [p for p in products if p["id"].startswith(product_filter)]
        if not products:
            print(f"No products matching filter '{product_filter}'.")
            sys.exit(1)

    print(f"\nSheetCraft AI — Etsy Uploader")
    print(f"Products to upload: {len(products)}")
    if dry_run:
        print("[DRY RUN MODE — no API calls will be made]\n")

    results = {}
    for product in products:
        listing_id = upload_product(client, product, dry_run=dry_run)
        results[product["id"]] = listing_id

    # Summary
    print(f"\n{'='*60}")
    print("UPLOAD SUMMARY")
    print(f"{'='*60}")
    success = sum(1 for v in results.values() if v is not None)
    failed = sum(1 for v in results.values() if v is None)
    for pid, lid in results.items():
        status = f"listing #{lid}" if lid else ("skipped (dry run)" if dry_run else "FAILED")
        print(f"  {pid}: {status}")
    if not dry_run:
        print(f"\nTotal: {success} succeeded, {failed} failed out of {len(results)}")
    print("\nAll listings are created as DRAFTS. Review them on Etsy before publishing.")


if __name__ == "__main__":
    main()
