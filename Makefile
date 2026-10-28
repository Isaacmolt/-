.PHONY: all generate check bundle catalog clean images upload-kit upload-gumroad upload-etsy sitecraft-leads sitecraft-sites sitecraft-sample sitecraft-preview sitecraft-send sitecraft-due sitecraft-stats

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

# ---------------------------------------------------------------------------
# SiteCraft — 在地商家官網代工（說明見 sitecraft/README.md）
#   make sitecraft-leads CITY=台中市 DISTRICT=西區 TYPE=咖啡廳
# ---------------------------------------------------------------------------
CITY ?= 台中市
DISTRICT ?=
TYPE ?=

sitecraft-leads:
	python sitecraft/find_leads.py --city "$(CITY)" $(if $(DISTRICT),--district "$(DISTRICT)") $(if $(TYPE),--type "$(TYPE)")

sitecraft-sites:
	python sitecraft/build_site.py

sitecraft-sample:
	python sitecraft/build_site.py --sample

sitecraft-preview:
	python sitecraft/send_outreach.py --stage first

sitecraft-send:
	python sitecraft/send_outreach.py --stage first --send

sitecraft-due:
	python sitecraft/crm.py due

sitecraft-stats:
	python sitecraft/crm.py stats
