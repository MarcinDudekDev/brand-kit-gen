# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Brand Kit Generator extracts brand colors from a website's CSS and generates a complete favicon set + OG image.

## Generation Methods

| Method | Flag | Notes |
|--------|------|-------|
| **HTML** | `--method html` (default) | Playwright rendering, best quality, FREE |
| PIL | `--method pil` | Pillow fallback, no extra deps |
| AI | `--method ai` or `--ai` | External APIs (most require keys) |

## Commands

```bash
# Activate venv first
source .venv/bin/activate

# Basic usage (HTML mode, default)
python brand_kit_gen.py https://example.com -v

# PIL fallback (if Playwright not installed)
python brand_kit_gen.py https://example.com --method pil -v

# AI mode
python brand_kit_gen.py https://example.com --ai -v

# Override colors
python brand_kit_gen.py https://example.com --primary "#2c3539" --accent "#e8a568"
```

## First-time Setup

```bash
pip install -r requirements.txt
playwright install chromium  # Required for HTML mode
```

## Architecture

```
brand_kit_gen.py          # CLI entry point
├── extractors/
│   ├── color_extractor.py    # CSS → color palette
│   └── brand_extractor.py    # og:site_name, title → brand name
├── generators/
│   ├── html_generator.py     # HTML/Playwright rendering (DEFAULT)
│   ├── pil_generator.py      # PIL fallback (3 styles)
│   ├── ai_generator.py       # OpenAI/Pollinations/Gemini
│   └── favicon_builder.py    # Logo → favicon set
├── models/
│   └── brand_identity.py     # BrandIdentity dataclass
└── utils/
    └── color_utils.py        # Color utilities
```

## Data Flow

1. `ColorExtractor` → parses CSS variables (`--primary`, `--accent`, `--background`)
2. `BrandExtractor` → extracts name from og:site_name > title > h1 > domain
3. `HTMLGenerator` (or PIL/AI) → creates 512x512 logo + 1200x630 OG image
4. `FaviconBuilder` → resizes logo to all favicon sizes

## Output Files

```
favicon.ico, favicon-16x16.png, favicon-32x32.png
apple-touch-icon.png (180), android-chrome-*.png (192, 512)
og-image.png (1200x630), site.webmanifest, preview.html
```

## Dependencies

- requests, beautifulsoup4, Pillow (required)
- playwright (for HTML mode, recommended)
- google-genai (optional, for Gemini AI)
