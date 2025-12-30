#!/usr/bin/env python3
"""Brand Kit Generator - Web UI with FastAPI + Datastar."""
import asyncio
import hashlib
import io
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from extractors.color_extractor import ColorExtractor
from extractors.brand_extractor import BrandExtractor
from generators.html_generator import HTMLGenerator
from generators.favicon_builder import build_favicon_set
from models.brand_identity import BrandIdentity, StyleConfig, BG_EFFECTS

app = FastAPI(title="Brand Kit Generator")

# Simple LRU cache for generated images (max 50 items)
_image_cache: OrderedDict[str, bytes] = OrderedDict()
_CACHE_MAX_SIZE = 50


def _cache_key(*args) -> str:
    """Generate cache key from arguments."""
    return hashlib.md5(str(args).encode()).hexdigest()


def _get_cached(key: str) -> Optional[bytes]:
    """Get item from cache, move to end (LRU)."""
    if key in _image_cache:
        _image_cache.move_to_end(key)
        return _image_cache[key]
    return None


def _set_cached(key: str, value: bytes):
    """Set item in cache, evict oldest if full."""
    _image_cache[key] = value
    _image_cache.move_to_end(key)
    while len(_image_cache) > _CACHE_MAX_SIZE:
        _image_cache.popitem(last=False)

# Setup templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Serve static files from output directory
app.mount("/static", StaticFiles(directory=BASE_DIR / "output"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/extract")
async def extract_brand(url: str):
    """Extract brand identity from URL."""
    try:
        # Extract colors
        color_extractor = ColorExtractor()
        color_data = color_extractor.extract_from_url(url)

        # Extract brand info
        brand_extractor = BrandExtractor()
        brand_data = brand_extractor.extract_from_url(url)

        return {
            "success": True,
            "name": brand_data.get("name", "Brand"),
            "tagline": brand_data.get("tagline", ""),
            "primary": color_data.get("primary", "#333333"),
            "accent": color_data.get("accent", "#666666"),
            "background": color_data.get("background", "#ffffff"),
            "text": color_data.get("text", "#ffffff"),
            "theme": color_data.get("theme", "light"),
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


def create_brand_identity(
    name: str,
    tagline: str = "",
    primary: str = "#333333",
    accent: str = "#666666",
    background: str = "#ffffff",
    text: str = "#ffffff",
    theme: str = "light",
) -> BrandIdentity:
    """Create BrandIdentity from parameters."""
    return BrandIdentity(
        name=name,
        domain="",
        colors=[],
        primary_color=primary,
        accent_color=accent,
        background_color=background,
        text_color=text,
        theme=theme,
        tagline=tagline,
    )


def parse_bool(val) -> bool:
    """Parse boolean from string or bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'yes')
    return bool(val)


def create_style_config(
    glow: float = 1.0,
    depth: float = 1.0,
    decoration: float = 1.0,
    gradient_angle: int = 160,
    font: str = "Inter",
    font_weight: int = 800,
    show_accent_line = True,
    show_bottom_bar = True,
    show_blobs = True,
    show_glow = True,
    bg_effect: str = "aurora",
) -> StyleConfig:
    """Create StyleConfig from parameters."""
    return StyleConfig(
        glow=glow,
        depth=depth,
        decoration=decoration,
        gradient_angle=gradient_angle,
        font=font,
        font_weight=font_weight,
        show_accent_line=parse_bool(show_accent_line),
        show_bottom_bar=parse_bool(show_bottom_bar),
        show_blobs=parse_bool(show_blobs),
        show_glow=parse_bool(show_glow),
        bg_effect=bg_effect,
    )


@app.get("/effects")
async def get_effects():
    """Return available background effects."""
    return BG_EFFECTS


@app.get("/preview/logo.html", response_class=HTMLResponse)
async def preview_logo_html(
    name: str = Query(...),
    primary: str = Query("#333333"),
    accent: str = Query("#666666"),
    background: str = Query("#ffffff"),
    glow: float = Query(1.0),
    depth: float = Query(1.0),
    font: str = Query("Inter"),
    fontWeight: int = Query(800),
    showGlow: str = Query("true"),
):
    """Return raw HTML for logo preview (instant, no Playwright)."""
    brand = create_brand_identity(
        name=name,
        primary=primary,
        accent=accent,
        background=background,
    )
    style = create_style_config(
        glow=glow,
        depth=depth,
        font=font,
        font_weight=fontWeight,
        show_glow=showGlow,
    )
    generator = HTMLGenerator(brand, style=style)
    html = generator.get_logo_html(size=512)

    # Scale to viewport for iframe
    scaled_html = html.replace(
        'width: 512px;\n            height: 512px;',
        'width: 100vw;\n            height: 100vh;'
    ).replace(
        'width: 492px;\n            height: 492px;',
        'width: 96vw;\n            height: 96vh;'
    ).replace(
        'border-radius: 102px;',
        'border-radius: 20%;'
    ).replace(
        'font-size: 215px;',
        'font-size: 42vw;'
    ).replace(
        'letter-spacing: -4px;',
        'letter-spacing: -0.8vw;'
    )
    return scaled_html


@app.get("/preview/og.html", response_class=HTMLResponse)
async def preview_og_html(
    name: str = Query(...),
    tagline: str = Query(""),
    primary: str = Query("#333333"),
    accent: str = Query("#666666"),
    background: str = Query("#ffffff"),
    text: str = Query("#ffffff"),
    theme: str = Query("light"),
    glow: float = Query(1.0),
    depth: float = Query(1.0),
    decoration: float = Query(1.0),
    gradientAngle: int = Query(160),
    font: str = Query("Inter"),
    fontWeight: int = Query(800),
    showAccentLine: str = Query("true"),
    showBottomBar: str = Query("true"),
    showBlobs: str = Query("true"),
    showGlow: str = Query("true"),
    bgEffect: str = Query("aurora"),
):
    """Return raw HTML for OG image preview (instant, no Playwright).

    Uses 100vw/100vh to fill iframe while maintaining design proportions.
    """
    brand = create_brand_identity(
        name=name,
        tagline=tagline,
        primary=primary,
        accent=accent,
        background=background,
        text=text,
        theme=theme,
    )
    style = create_style_config(
        glow=glow,
        depth=depth,
        decoration=decoration,
        gradient_angle=gradientAngle,
        font=font,
        font_weight=fontWeight,
        show_accent_line=showAccentLine,
        show_bottom_bar=showBottomBar,
        show_blobs=showBlobs,
        show_glow=showGlow,
        bg_effect=bgEffect,
    )
    generator = HTMLGenerator(brand, style=style)
    # Get full-size HTML and wrap with scaling
    html = generator.get_og_html(width=1200, height=630)

    # Wrap to scale to iframe viewport
    scaled_html = html.replace(
        'width: 1200px;\n            height: 630px;',
        'width: 100vw;\n            height: 100vh;'
    ).replace(
        'font-size: 88px;',
        'font-size: 7.3vw;'  # 88/1200 ≈ 7.3%
    ).replace(
        'font-size: 26px;',
        'font-size: 2.2vw;'  # 26/1200 ≈ 2.2%
    ).replace(
        'font-size: 24px;',
        'font-size: 2vw;'
    ).replace(
        'font-size: 22px;',
        'font-size: 1.8vw;'
    ).replace(
        'font-size: 20px;',
        'font-size: 1.7vw;'
    )
    return scaled_html


def _generate_logo_sync(brand: BrandIdentity, style: StyleConfig) -> bytes:
    """Generate logo in sync context (for thread pool)."""
    generator = HTMLGenerator(brand, style=style)
    img = generator.generate_logo(size=512)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@app.get("/preview/logo")
async def preview_logo(
    name: str = Query(...),
    primary: str = Query("#333333"),
    accent: str = Query("#666666"),
    background: str = Query("#ffffff"),
    glow: float = Query(1.0),
    depth: float = Query(1.0),
    font: str = Query("Inter"),
    fontWeight: int = Query(800),
    showGlow: str = Query("true"),
):
    """Generate logo preview PNG (with caching)."""
    cache_key = _cache_key("logo", name, primary, accent, background, glow, depth, font, fontWeight, showGlow)

    # Check cache first
    cached = _get_cached(cache_key)
    if cached:
        return StreamingResponse(io.BytesIO(cached), media_type="image/png")

    brand = create_brand_identity(
        name=name,
        primary=primary,
        accent=accent,
        background=background,
    )
    style = create_style_config(
        glow=glow,
        depth=depth,
        font=font,
        font_weight=fontWeight,
        show_glow=showGlow,
    )

    # Run Playwright in thread pool (sync API doesn't work in async)
    png_bytes = await asyncio.to_thread(_generate_logo_sync, brand, style)

    # Cache the result
    _set_cached(cache_key, png_bytes)

    return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png")


def _generate_og_sync(brand: BrandIdentity, style: StyleConfig) -> bytes:
    """Generate OG image in sync context (for thread pool)."""
    generator = HTMLGenerator(brand, style=style)
    img = generator.generate_og_image()
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@app.get("/preview/og")
async def preview_og(
    name: str = Query(...),
    tagline: str = Query(""),
    primary: str = Query("#333333"),
    accent: str = Query("#666666"),
    background: str = Query("#ffffff"),
    text: str = Query("#ffffff"),
    theme: str = Query("light"),
    glow: float = Query(1.0),
    depth: float = Query(1.0),
    decoration: float = Query(1.0),
    gradientAngle: int = Query(160),
    font: str = Query("Inter"),
    fontWeight: int = Query(800),
    showAccentLine: str = Query("true"),
    showBottomBar: str = Query("true"),
    showBlobs: str = Query("true"),
    showGlow: str = Query("true"),
    bgEffect: str = Query("aurora"),
):
    """Generate OG image preview PNG (with caching)."""
    cache_key = _cache_key("og", name, tagline, primary, accent, background, text, theme,
                          glow, depth, decoration, gradientAngle, font, fontWeight,
                          showAccentLine, showBottomBar, showBlobs, showGlow, bgEffect)

    # Check cache first
    cached = _get_cached(cache_key)
    if cached:
        return StreamingResponse(io.BytesIO(cached), media_type="image/png")

    brand = create_brand_identity(
        name=name,
        tagline=tagline,
        primary=primary,
        accent=accent,
        background=background,
        text=text,
        theme=theme,
    )
    style = create_style_config(
        glow=glow,
        depth=depth,
        decoration=decoration,
        gradient_angle=gradientAngle,
        font=font,
        font_weight=fontWeight,
        show_accent_line=showAccentLine,
        show_bottom_bar=showBottomBar,
        show_blobs=showBlobs,
        show_glow=showGlow,
        bg_effect=bgEffect,
    )

    # Run Playwright in thread pool (sync API doesn't work in async)
    png_bytes = await asyncio.to_thread(_generate_og_sync, brand, style)

    # Cache the result
    _set_cached(cache_key, png_bytes)

    return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png")


def _generate_zip_sync(brand: BrandIdentity, style: StyleConfig) -> bytes:
    """Generate ZIP in sync context (for thread pool)."""
    import tempfile

    generator = HTMLGenerator(brand, style=style)
    logo = generator.generate_logo(size=512)
    og_image = generator.generate_og_image()

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            generated = build_favicon_set(
                source=logo,
                output_dir=tmpdir,
                theme_color=brand.primary_color,
                verbose=False,
            )
            for filepath in generated.values():
                zf.write(filepath, filepath.name)

        og_buffer = io.BytesIO()
        og_image.save(og_buffer, format="PNG")
        zf.writestr("og-image.png", og_buffer.getvalue())

        manifest = f'''{{"name":"{brand.name}","short_name":"{brand.name}","icons":[{{"src":"android-chrome-192x192.png","sizes":"192x192","type":"image/png"}},{{"src":"android-chrome-512x512.png","sizes":"512x512","type":"image/png"}}],"theme_color":"{brand.primary_color}","background_color":"{brand.background_color}","display":"standalone"}}'''
        zf.writestr("site.webmanifest", manifest)

        readme = f"""# {brand.name} Brand Kit

## Files Included
- favicon.ico (16, 32, 48px multi-size)
- favicon-16x16.png
- favicon-32x32.png
- apple-touch-icon.png (180x180)
- android-chrome-192x192.png
- android-chrome-512x512.png
- og-image.png (1200x630)
- site.webmanifest

## Usage

Add to your HTML <head>:

```html
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="{brand.primary_color}">
<meta property="og:image" content="/og-image.png">
```

## Colors
- Primary: {brand.primary_color}
- Accent: {brand.accent_color}
- Background: {brand.background_color}

Generated with Brand Kit Generator
"""
        zf.writestr("README.md", readme)

    return zip_buffer.getvalue()


@app.get("/download")
async def download_zip(
    name: str = Query(...),
    tagline: str = Query(""),
    primary: str = Query("#333333"),
    accent: str = Query("#666666"),
    background: str = Query("#ffffff"),
    text: str = Query("#ffffff"),
    theme: str = Query("light"),
    glow: float = Query(1.0),
    depth: float = Query(1.0),
    decoration: float = Query(1.0),
    gradientAngle: int = Query(160),
    font: str = Query("Inter"),
    fontWeight: int = Query(800),
    showAccentLine: str = Query("true"),
    showBottomBar: str = Query("true"),
    showBlobs: str = Query("true"),
    showGlow: str = Query("true"),
    bgEffect: str = Query("aurora"),
):
    """Generate and download ZIP with all brand assets."""
    brand = create_brand_identity(
        name=name,
        tagline=tagline,
        primary=primary,
        accent=accent,
        background=background,
        text=text,
        theme=theme,
    )
    style = create_style_config(
        glow=glow,
        depth=depth,
        decoration=decoration,
        gradient_angle=gradientAngle,
        font=font,
        font_weight=fontWeight,
        show_accent_line=showAccentLine,
        show_bottom_bar=showBottomBar,
        show_blobs=showBlobs,
        show_glow=showGlow,
        bg_effect=bgEffect,
    )

    # Run in thread pool (Playwright sync API)
    zip_bytes = await asyncio.to_thread(_generate_zip_sync, brand, style)

    # Create safe filename
    safe_name = "".join(c if c.isalnum() else "-" for c in brand.name.lower())

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}-brand-kit.zip"'
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
