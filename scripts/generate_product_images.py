#!/usr/bin/env python3
"""
Generate professional Etsy listing images for all 10 SheetCraft AI products.
Each product gets 3 images (2700x2025 PNG): hero.png, features.png, steps.png
"""

import json
import os
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont

# ─── Constants ───────────────────────────────────────────────────────────────

BASE_DIR = "/home/user/-"
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")
PRODUCTS_DIR = os.path.join(BASE_DIR, "products")

WIDTH, HEIGHT = 2700, 2025

COLOR_DARK_GREEN = "#2D5F2D"
COLOR_CREAM = "#F5F0E8"
COLOR_GOLD_BROWN = "#D4A574"
COLOR_WHITE = "#FFFFFF"
COLOR_BLACK = "#222222"
COLOR_LIGHT_GREEN = "#3A7A3A"

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# For checkmarks and special chars, DejaVu has good Unicode coverage
FONT_SYMBOL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def draw_text_centered(draw, y, text, font, fill, width=WIDTH):
    """Draw text horizontally centered at given y."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


def draw_text_wrapped_centered(draw, y, text, font, fill, max_width, line_spacing=20):
    """Draw long text wrapped and centered."""
    # Estimate chars per line
    avg_char_w = draw.textbbox((0, 0), "M", font=font)[2]
    chars_per_line = max(10, int(max_width / avg_char_w))
    lines = textwrap.wrap(text, width=chars_per_line)
    total_h = 0
    for line in lines:
        h = draw_text_centered(draw, y + total_h, line, font, fill)
        total_h += h + line_spacing
    return total_h


def extract_features(listing_path, max_features=5):
    """Extract bullet-point features from listing-description.txt."""
    if not os.path.exists(listing_path):
        return ["Professional Google Sheets Template",
                "Automatic Calculations",
                "Visual Dashboard",
                "Fully Customizable",
                "Instant Download"]

    with open(listing_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the WHAT'S INCLUDED section
    features = []
    in_section = False
    for line in content.splitlines():
        stripped = line.strip()

        if "WHAT'S INCLUDED" in stripped.upper() or "WHAT YOU GET" in stripped.upper():
            in_section = True
            continue

        if in_section:
            # Check for bullet lines (✔, -, •)
            m = re.match(r'^[✔✓\-•]\s*(.+)', stripped)
            if m:
                # Clean up: take just the main feature name (before —)
                feat = m.group(1).strip()
                # Shorten if it has a long dash description
                if " — " in feat:
                    feat = feat.split(" — ")[0].strip()
                elif " - " in feat:
                    parts = feat.split(" - ", 1)
                    if len(parts[0]) < 40:
                        feat = parts[0].strip()
                features.append(feat)
                if len(features) >= max_features:
                    break

            # Stop if we hit the next section
            if stripped and not m and len(features) > 0:
                if stripped.startswith("━") or stripped.isupper():
                    break

    if not features:
        # Fallback: grab any bullet lines
        for line in content.splitlines():
            stripped = line.strip()
            m = re.match(r'^[✔✓\-•]\s*(.+)', stripped)
            if m:
                feat = m.group(1).strip()
                if " — " in feat:
                    feat = feat.split(" — ")[0].strip()
                features.append(feat)
                if len(features) >= max_features:
                    break

    if not features:
        features = ["Professional Template", "Auto Calculations",
                     "Visual Dashboard", "Customizable", "Instant Download"]

    return features


def draw_brand_bar(draw, text="SheetCraft AI", bg_color=COLOR_CREAM,
                   text_color=COLOR_DARK_GREEN, bar_height=120):
    """Draw brand bar at the bottom of the image."""
    y_bar = HEIGHT - bar_height
    draw.rectangle([0, y_bar, WIDTH, HEIGHT], fill=bg_color)
    font = load_font(FONT_BOLD, 48)
    draw_text_centered(draw, y_bar + (bar_height - 48) // 2, text, font, text_color)


def draw_decorative_line(draw, y, color, width_pct=0.3, thickness=4):
    """Draw a centered decorative line."""
    line_w = int(WIDTH * width_pct)
    x_start = (WIDTH - line_w) // 2
    draw.rectangle([x_start, y, x_start + line_w, y + thickness], fill=color)


# ─── Image Generators ────────────────────────────────────────────────────────

def generate_hero(product_name, output_path):
    """Generate hero.png — main listing image."""
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_DARK_GREEN)
    draw = ImageDraw.Draw(img)

    # Decorative top accent line
    draw.rectangle([0, 0, WIDTH, 12], fill=COLOR_GOLD_BROWN)

    # Small top label
    font_small = load_font(FONT_REGULAR, 48)
    draw_text_centered(draw, 280, "SheetCraft AI Presents", font_small, COLOR_GOLD_BROWN)

    # Decorative line
    draw_decorative_line(draw, 370, COLOR_GOLD_BROWN, 0.15, 3)

    # Main product name — large, white, centered
    # Adjust font size based on name length
    if len(product_name) <= 20:
        title_size = 140
    elif len(product_name) <= 30:
        title_size = 120
    else:
        title_size = 100

    font_title = load_font(FONT_BOLD, title_size)

    # Wrap if needed
    bbox_test = draw.textbbox((0, 0), product_name, font=font_title)
    text_w = bbox_test[2] - bbox_test[0]

    if text_w > WIDTH - 200:
        # Wrap into multiple lines
        y_start = 550
        draw_text_wrapped_centered(draw, y_start, product_name, font_title,
                                   COLOR_WHITE, WIDTH - 200, line_spacing=30)
    else:
        y_title = 650 - title_size // 2
        draw_text_centered(draw, y_title, product_name, font_title, COLOR_WHITE)

    # Subtitle line 1
    font_sub = load_font(FONT_REGULAR, 56)
    draw_text_centered(draw, 850, "Google Sheets Template | Instant Download",
                       font_sub, COLOR_GOLD_BROWN)

    # Decorative line below subtitle
    draw_decorative_line(draw, 940, COLOR_GOLD_BROWN, 0.2, 3)

    # Feature highlights in a subtle way
    font_feat = load_font(FONT_REGULAR, 42)
    features_text = [
        "Professional Design",
        "Automatic Calculations",
        "Ready to Use"
    ]
    y_feat = 1050
    for ft in features_text:
        draw_text_centered(draw, y_feat, f"- {ft} -", font_feat, "#A8C9A8")
        y_feat += 70

    # Decorative border (inner rectangle)
    margin = 60
    border_color = COLOR_GOLD_BROWN
    draw.rectangle(
        [margin, margin, WIDTH - margin, HEIGHT - 140],
        outline=border_color, width=3
    )
    draw.rectangle(
        [margin + 15, margin + 15, WIDTH - margin - 15, HEIGHT - 155],
        outline=border_color, width=1
    )

    # Bottom cream bar with brand
    draw_brand_bar(draw, "SheetCraft AI", COLOR_CREAM, COLOR_DARK_GREEN, 120)

    # Accent at very bottom
    draw.rectangle([0, HEIGHT - 8, WIDTH, HEIGHT], fill=COLOR_GOLD_BROWN)

    img.save(output_path, "PNG")


def generate_features(product_name, features, output_path):
    """Generate features.png — what's included."""
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_CREAM)
    draw = ImageDraw.Draw(img)

    # Top green accent bar
    bar_h = 14
    draw.rectangle([0, 0, WIDTH, bar_h], fill=COLOR_DARK_GREEN)

    # Title
    font_title = load_font(FONT_BOLD, 100)
    draw_text_centered(draw, 150, "What's Included", font_title, COLOR_DARK_GREEN)

    # Decorative line under title
    draw_decorative_line(draw, 290, COLOR_DARK_GREEN, 0.12, 4)

    # Product name subtitle
    font_sub = load_font(FONT_REGULAR, 48)
    draw_text_centered(draw, 340, product_name, font_sub, COLOR_GOLD_BROWN)

    # Feature list
    font_check = load_font(FONT_SYMBOL, 60)
    font_feat = load_font(FONT_REGULAR, 56)

    y_start = 520
    x_left = 350
    spacing = 180

    for i, feat in enumerate(features):
        y = y_start + i * spacing

        # Green circle background for checkmark
        circle_x = x_left
        circle_y = y + 5
        circle_r = 38
        draw.ellipse(
            [circle_x - circle_r, circle_y - circle_r,
             circle_x + circle_r, circle_y + circle_r],
            fill=COLOR_DARK_GREEN
        )

        # White checkmark
        font_ck = load_font(FONT_BOLD, 44)
        ck_bbox = draw.textbbox((0, 0), "✓", font=font_ck)
        ck_w = ck_bbox[2] - ck_bbox[0]
        ck_h = ck_bbox[3] - ck_bbox[1]
        draw.text(
            (circle_x - ck_w // 2, circle_y - ck_h // 2 - 4),
            "✓", font=font_ck, fill=COLOR_WHITE
        )

        # Feature text — truncate if too wide
        max_text_w = WIDTH - x_left - 70 - 150  # leave right margin
        display_feat = feat
        while True:
            bbox_f = draw.textbbox((0, 0), display_feat, font=font_feat)
            if bbox_f[2] - bbox_f[0] <= max_text_w or len(display_feat) <= 10:
                break
            display_feat = display_feat[:len(display_feat) - 2].rstrip() + "..."
        draw.text((x_left + 70, y - 18), display_feat, font=font_feat, fill=COLOR_BLACK)

        # Subtle separator line (except after last)
        if i < len(features) - 1:
            line_y = y + spacing - 50
            draw.rectangle(
                [x_left + 70, line_y, WIDTH - 350, line_y + 1],
                fill="#D0CBBC"
            )

    # Bottom brand bar (dark green)
    bar_height = 120
    y_bar = HEIGHT - bar_height
    draw.rectangle([0, y_bar, WIDTH, HEIGHT], fill=COLOR_DARK_GREEN)
    font_brand = load_font(FONT_BOLD, 48)
    draw_text_centered(draw, y_bar + (bar_height - 48) // 2,
                       "SheetCraft AI", font_brand, COLOR_CREAM)

    # Bottom accent
    draw.rectangle([0, HEIGHT - 8, WIDTH, HEIGHT], fill=COLOR_GOLD_BROWN)

    img.save(output_path, "PNG")


def generate_steps(product_name, output_path):
    """Generate steps.png — how it works."""
    img = Image.new("RGB", (WIDTH, HEIGHT), COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    # Top accent
    draw.rectangle([0, 0, WIDTH, 14], fill=COLOR_DARK_GREEN)

    # Title
    font_title = load_font(FONT_BOLD, 100)
    draw_text_centered(draw, 150, "How It Works", font_title, COLOR_DARK_GREEN)

    # Decorative line
    draw_decorative_line(draw, 290, COLOR_DARK_GREEN, 0.12, 4)

    # Subtitle
    font_sub = load_font(FONT_REGULAR, 44)
    draw_text_centered(draw, 340, "Get started in 3 simple steps", font_sub, "#888888")

    # Steps
    steps = [
        ("1", "Download the file"),
        ("2", "Open in Google Sheets"),
        ("3", "Start tracking automatically!"),
    ]

    font_num = load_font(FONT_BOLD, 80)
    font_step = load_font(FONT_REGULAR, 60)

    y_start = 550
    step_spacing = 280

    for i, (num, text) in enumerate(steps):
        y = y_start + i * step_spacing

        # Circle with number
        circle_x = WIDTH // 2 - 400
        circle_y = y + 30
        circle_r = 55
        draw.ellipse(
            [circle_x - circle_r, circle_y - circle_r,
             circle_x + circle_r, circle_y + circle_r],
            fill=COLOR_DARK_GREEN
        )
        # Number in circle
        num_bbox = draw.textbbox((0, 0), num, font=font_num)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]
        draw.text(
            (circle_x - num_w // 2, circle_y - num_h // 2 - 12),
            num, font=font_num, fill=COLOR_WHITE
        )

        # Step text
        text_x = circle_x + circle_r + 50
        text_bbox = draw.textbbox((0, 0), text, font=font_step)
        text_h = text_bbox[3] - text_bbox[1]
        draw.text((text_x, circle_y - text_h // 2 - 5), text,
                  font=font_step, fill=COLOR_BLACK)

        # Connecting line between steps (except after last)
        if i < len(steps) - 1:
            line_x = circle_x
            draw.rectangle(
                [line_x - 2, circle_y + circle_r + 10,
                 line_x + 2, circle_y + step_spacing - circle_r - 10],
                fill="#CCCCCC"
            )

    # CTA banner
    cta_y = 1580
    cta_h = 120
    draw.rectangle([200, cta_y, WIDTH - 200, cta_y + cta_h],
                   fill=COLOR_DARK_GREEN)
    # Rounded feel with small circles at ends
    font_cta = load_font(FONT_BOLD, 52)
    draw_text_centered(draw, cta_y + (cta_h - 52) // 2,
                       "Instant Download  —  Start Now", font_cta, COLOR_WHITE)

    # Bottom brand bar
    bar_height = 120
    y_bar = HEIGHT - bar_height
    draw.rectangle([0, y_bar, WIDTH, HEIGHT], fill=COLOR_CREAM)
    font_brand = load_font(FONT_BOLD, 48)
    draw_text_centered(draw, y_bar + (bar_height - 48) // 2,
                       "SheetCraft AI", font_brand, COLOR_DARK_GREEN)

    # Bottom accent
    draw.rectangle([0, HEIGHT - 8, WIDTH, HEIGHT], fill=COLOR_GOLD_BROWN)

    img.save(output_path, "PNG")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    # Load catalog
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    products = catalog["products"]
    print(f"Generating images for {len(products)} products...\n")

    for product in products:
        pid = product["id"]
        name = product["name"]
        product_dir = os.path.join(PRODUCTS_DIR, pid)
        images_dir = os.path.join(product_dir, "images")
        listing_path = os.path.join(product_dir, "listing-description.txt")

        os.makedirs(images_dir, exist_ok=True)

        # Extract features
        features = extract_features(listing_path)

        # Generate all 3 images
        hero_path = os.path.join(images_dir, "hero.png")
        features_path = os.path.join(images_dir, "features.png")
        steps_path = os.path.join(images_dir, "steps.png")

        generate_hero(name, hero_path)
        print(f"  [+] {pid}/images/hero.png")

        generate_features(name, features, features_path)
        print(f"  [+] {pid}/images/features.png")

        generate_steps(name, steps_path)
        print(f"  [+] {pid}/images/steps.png")

        print(f"  Done: {name}\n")

    print(f"All images generated! ({len(products) * 3} files total)")


if __name__ == "__main__":
    main()
