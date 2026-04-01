.PHONY: all generate check bundle catalog clean images upload-kit upload-gumroad upload-etsy

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
