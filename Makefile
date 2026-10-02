.PHONY: all generate check bundle catalog clean images upload-kit upload-gumroad upload-etsy shopee-all shopee-niches shopee-links shopee-posts shopee-tracker shopee-roi shopee-app shopee-autopost-dry

all: generate check bundle catalog

generate:
	python scripts/generate_all.py

check:
	python scripts/quality_check.py

bundle:
	python scripts/bundle_generator.py

catalog:
	python scripts/product_catalog.py

clean:
	find products -name '*.xlsx' -delete 2>/dev/null || true
	find bundles -name '*.zip' -delete 2>/dev/null || true
	@echo "Cleaned all .xlsx and .zip files."

images:
	@python -c "import PIL" 2>/dev/null || { echo "Pillow not installed. Run: pip install Pillow"; exit 1; }
	@if [ -f scripts/generate_images.py ]; then \
		python scripts/generate_images.py; \
	else \
		echo "No image generator script found at scripts/generate_images.py"; \
	fi

upload-kit:
	python scripts/generate_upload_kit.py

upload-gumroad:
	@python -c "from playwright.sync_api import sync_playwright" 2>/dev/null || { echo "請先安裝: pip install playwright && playwright install chromium"; exit 1; }
	python scripts/auto_upload_gumroad.py

upload-etsy:
	@python -c "from playwright.sync_api import sync_playwright" 2>/dev/null || { echo "請先安裝: pip install playwright && playwright install chromium"; exit 1; }
	python scripts/auto_upload_etsy.py

# ── 蝦皮分潤（shopee-affiliate/）───────────────────────────────────
shopee-all: shopee-niches shopee-links shopee-posts shopee-tracker shopee-roi

shopee-niches:
	python scripts/shopee_niche_scorer.py

shopee-links:
	python scripts/shopee_link_builder.py

shopee-posts:
	python scripts/shopee_post_generator.py

shopee-tracker:
	@python -c "import openpyxl" 2>/dev/null || { echo "請先安裝: pip install -r scripts/requirements.txt"; exit 1; }
	python scripts/shopee_tracker.py

shopee-roi:
	python scripts/shopee_roi_calc.py

shopee-app:
	python scripts/shopee_app_seed.py

shopee-autopost-dry:
	python scripts/threads_autopost.py --dry-run
