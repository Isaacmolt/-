.PHONY: all generate check bundle catalog clean images

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
