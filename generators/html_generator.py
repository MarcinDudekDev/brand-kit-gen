"""HTML/CSS-based image generator using Playwright."""
import io
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from models.brand_identity import BrandIdentity, StyleConfig


# Check if Playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


def is_playwright_available() -> bool:
    """Check if Playwright is installed and browser is available."""
    if not PLAYWRIGHT_AVAILABLE:
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
            return True
    except Exception:
        return False


class HTMLGenerator:
    """Generate logos and OG images by rendering HTML/CSS with Playwright."""

    def __init__(self, brand: BrandIdentity, style: Optional[StyleConfig] = None):
        self.brand = brand
        self.style = style or StyleConfig()

        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    def get_logo_html(self, size: int = 512) -> str:
        """Get HTML for logo (for live preview).

        Args:
            size: Image size (square)

        Returns:
            HTML string
        """
        return self._build_logo_html(size)

    def _build_logo_html(self, size: int = 512) -> str:
        """Build HTML for logo."""
        # Calculate proportional sizes
        border_radius = size // 5
        font_size = int(size * 0.42)
        inner_size = size - 20

        # RGB strings for rgba()
        accent_rgb = self._hex_to_rgb_str(self.brand.accent_color)
        primary_rgb = self._hex_to_rgb_str(self.brand.primary_color)

        # URL-encode font name for Google Fonts
        font_encoded = self.style.font.replace(' ', '+')

        return f'''<!DOCTYPE html>
<html>
<head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family={font_encoded}:wght@{self.style.font_weight}&display=swap');

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            width: {size}px;
            height: {size}px;
            display: flex;
            justify-content: center;
            align-items: center;
            background: transparent;
        }}

        .logo {{
            width: {inner_size}px;
            height: {inner_size}px;
            border-radius: {border_radius}px;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            overflow: hidden;

            /* Gradient background with depth */
            background:
                /* Subtle inner glow */
                radial-gradient(
                    circle at 30% 30%,
                    rgba(255, 255, 255, 0.1) 0%,
                    transparent 50%
                ),
                /* Main gradient */
                linear-gradient(
                    145deg,
                    {self._blend_colors(self.brand.primary_color, '#ffffff', 0.08)} 0%,
                    {self.brand.primary_color} 50%,
                    {self._blend_colors(self.brand.primary_color, '#000000', 0.15)} 100%
                );

            /* Premium shadow */
            box-shadow:
                0 8px 32px rgba(0, 0, 0, {0.3 * self.style.depth}),
                0 2px 8px rgba(0, 0, 0, {0.2 * self.style.depth}),
                inset 0 1px 0 rgba(255, 255, 255, {0.1 * self.style.depth});
        }}

        .initials {{
            color: {self.brand.accent_color};
            font-size: {font_size}px;
            font-weight: {self.style.font_weight};
            font-family: '{self.style.font}', -apple-system, BlinkMacSystemFont, sans-serif;
            letter-spacing: -4px;
            text-shadow:
                0 0 40px rgba({accent_rgb}, {0.5 * self.style.glow if self.style.show_glow else 0}),
                0 2px 4px rgba(0, 0, 0, {0.3 * self.style.depth});
        }}
    </style>
</head>
<body>
    <div class="logo">
        <span class="initials">{self.brand.initials}</span>
    </div>
</body>
</html>'''

    def generate_logo(self, size: int = 512) -> Image.Image:
        """Generate logo with premium gradient design.

        Args:
            size: Image size (square)

        Returns:
            PIL Image (RGBA)
        """
        html = self._build_logo_html(size)
        return self._render_html(html, size, size, transparent=True)

    def get_og_html(self, width: int = 1200, height: int = 630) -> str:
        """Get HTML for OG image (for live preview).

        Args:
            width: Image width
            height: Image height

        Returns:
            HTML string
        """
        return self._build_og_html(width, height)

    def _get_bg_effect_css(self, width: int, height: int) -> tuple[str, str]:
        """Get CSS for background effect.

        Returns:
            Tuple of (background CSS property value, extra HTML elements)
        """
        effect = self.style.bg_effect
        accent_rgb = self._hex_to_rgb_str(self.brand.accent_color)
        primary_rgb = self._hex_to_rgb_str(self.brand.primary_color)
        bg_rgb = self._hex_to_rgb_str(self.brand.background_color)
        dec = self.style.decoration
        angle = self.style.gradient_angle

        extra_html = ""

        if effect == 'aurora':
            # Original smooth radial blobs
            bg_css = f'''
                /* Accent blob - top right */
                radial-gradient(
                    ellipse 700px 500px at 85% 15%,
                    rgba({accent_rgb}, {0.35 * dec}) 0%,
                    rgba({accent_rgb}, {0.1 * dec}) 40%,
                    transparent 70%
                ),
                /* Primary blob - bottom left */
                radial-gradient(
                    ellipse 500px 400px at 10% 90%,
                    rgba({primary_rgb}, {0.25 * dec}) 0%,
                    rgba({primary_rgb}, {0.05 * dec}) 50%,
                    transparent 70%
                ),
                /* Subtle center glow */
                radial-gradient(
                    ellipse 800px 400px at 50% 50%,
                    rgba({primary_rgb}, {0.08 * dec}) 0%,
                    transparent 60%
                ),
                /* Base gradient */
                linear-gradient(
                    {angle}deg,
                    {self.brand.background_color} 0%,
                    {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.15)} 100%
                )'''

        elif effect == 'mesh':
            # Multi-point mesh gradient - 6 overlapping radials
            bg_css = f'''
                radial-gradient(ellipse 600px 400px at 20% 20%, rgba({accent_rgb}, {0.4 * dec}) 0%, transparent 60%),
                radial-gradient(ellipse 500px 500px at 80% 30%, rgba({primary_rgb}, {0.35 * dec}) 0%, transparent 55%),
                radial-gradient(ellipse 400px 350px at 60% 70%, rgba({accent_rgb}, {0.3 * dec}) 0%, transparent 50%),
                radial-gradient(ellipse 550px 400px at 10% 80%, rgba({primary_rgb}, {0.25 * dec}) 0%, transparent 60%),
                radial-gradient(ellipse 450px 300px at 90% 85%, rgba({accent_rgb}, {0.2 * dec}) 0%, transparent 50%),
                radial-gradient(ellipse 700px 500px at 50% 50%, rgba({primary_rgb}, {0.1 * dec}) 0%, transparent 70%),
                linear-gradient({angle}deg, {self.brand.background_color} 0%, {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.1)} 100%)'''

        elif effect == 'noise':
            # Grainy textured gradient with SVG noise overlay
            bg_css = f'''
                linear-gradient({angle}deg,
                    {self.brand.background_color} 0%,
                    {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.2)} 50%,
                    {self._blend_colors(self.brand.background_color, self.brand.accent_color, 0.15)} 100%)'''
            # Add SVG noise filter overlay
            extra_html = f'''
            <svg width="0" height="0" style="position:absolute">
                <filter id="grain">
                    <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/>
                    <feColorMatrix type="saturate" values="0"/>
                </filter>
            </svg>
            <div class="noise-overlay"></div>'''

        elif effect == 'waves':
            # Layered SVG wave curves
            wave_color1 = self._blend_colors(self.brand.primary_color, self.brand.background_color, 0.7)
            wave_color2 = self._blend_colors(self.brand.accent_color, self.brand.background_color, 0.8)
            bg_css = f'''linear-gradient({angle}deg, {self.brand.background_color} 0%, {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.1)} 100%)'''
            extra_html = f'''
            <svg class="wave-bg" viewBox="0 0 1200 630" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M0,500 C200,450 400,550 600,480 C800,410 1000,520 1200,470 L1200,630 L0,630 Z" fill="{wave_color1}" opacity="{0.4 * dec}"/>
                <path d="M0,530 C300,480 500,580 700,510 C900,440 1100,550 1200,500 L1200,630 L0,630 Z" fill="{wave_color2}" opacity="{0.3 * dec}"/>
                <path d="M0,560 C250,520 450,600 650,550 C850,500 1050,580 1200,540 L1200,630 L0,630 Z" fill="{self.brand.primary_color}" opacity="{0.2 * dec}"/>
            </svg>'''

        elif effect == 'spotlight':
            # Dramatic corner lighting
            bg_css = f'''
                radial-gradient(ellipse 1000px 800px at 95% 5%, rgba({accent_rgb}, {0.5 * dec}) 0%, transparent 50%),
                radial-gradient(ellipse 600px 600px at 90% 10%, rgba(255, 255, 255, {0.15 * dec}) 0%, transparent 40%),
                radial-gradient(ellipse 400px 400px at 5% 95%, rgba({primary_rgb}, {0.2 * dec}) 0%, transparent 50%),
                linear-gradient({angle}deg, {self.brand.background_color} 0%, {self._blend_colors(self.brand.background_color, '#000000', 0.1)} 100%)'''

        elif effect == 'minimal':
            # Clean simple gradient, no decorations
            bg_css = f'''linear-gradient({angle}deg, {self.brand.background_color} 0%, {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.15)} 100%)'''

        elif effect == 'glass':
            # Glassmorphism with blur
            bg_css = f'''linear-gradient({angle}deg, {self.brand.background_color} 0%, {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.15)} 100%)'''
            extra_html = f'''
            <div class="glass-shape glass-1"></div>
            <div class="glass-shape glass-2"></div>
            <div class="glass-shape glass-3"></div>'''

        elif effect == 'dots':
            # Subtle dot pattern overlay
            bg_css = f'''linear-gradient({angle}deg, {self.brand.background_color} 0%, {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.1)} 100%)'''
            # Tiled dots via overlay
            extra_html = f'''<div class="dots-overlay"></div>'''

        elif effect == 'diagonal':
            # Bold diagonal color split
            split_color = self._blend_colors(self.brand.primary_color, self.brand.background_color, 0.5)
            bg_css = f'''
                linear-gradient(135deg,
                    {self.brand.background_color} 0%,
                    {self.brand.background_color} 45%,
                    {split_color} 45%,
                    {split_color} 55%,
                    {self._blend_colors(self.brand.background_color, self.brand.accent_color, 0.2)} 55%,
                    {self._blend_colors(self.brand.background_color, self.brand.accent_color, 0.2)} 100%)'''

        elif effect == 'geometric':
            # Subtle geometric grid pattern
            bg_css = f'''linear-gradient({angle}deg, {self.brand.background_color} 0%, {self._blend_colors(self.brand.background_color, self.brand.primary_color, 0.08)} 100%)'''
            # Grid via overlay
            extra_html = f'''<div class="geo-overlay"></div>'''

        else:
            # Fallback to aurora
            return self._get_bg_effect_css_aurora(width, height, dec, accent_rgb, primary_rgb, angle)

        return bg_css, extra_html

    def _get_bg_effect_extra_styles(self) -> str:
        """Get extra CSS styles for background effects."""
        effect = self.style.bg_effect
        dec = self.style.decoration
        accent_rgb = self._hex_to_rgb_str(self.brand.accent_color)
        primary_rgb = self._hex_to_rgb_str(self.brand.primary_color)

        if effect == 'noise':
            return f'''
            .noise-overlay {{
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                filter: url(#grain);
                opacity: {0.12 * dec};
                mix-blend-mode: overlay;
                pointer-events: none;
                z-index: 2;
            }}'''

        elif effect == 'waves':
            return '''
            .wave-bg {
                position: absolute;
                bottom: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 1;
                pointer-events: none;
            }'''

        elif effect == 'glass':
            return f'''
            .glass-shape {{
                position: absolute;
                border-radius: 50%;
                background: linear-gradient(135deg,
                    rgba({accent_rgb}, {0.3 * dec}) 0%,
                    rgba({primary_rgb}, {0.1 * dec}) 100%);
                filter: blur(40px);
                z-index: 1;
            }}
            .glass-1 {{
                width: 400px; height: 400px;
                top: -100px; right: -50px;
            }}
            .glass-2 {{
                width: 300px; height: 300px;
                bottom: -80px; left: -60px;
                background: linear-gradient(135deg,
                    rgba({primary_rgb}, {0.25 * dec}) 0%,
                    rgba({accent_rgb}, {0.1 * dec}) 100%);
            }}
            .glass-3 {{
                width: 200px; height: 200px;
                top: 40%; left: 30%;
                background: rgba(255, 255, 255, {0.1 * dec});
                filter: blur(60px);
            }}'''

        elif effect == 'dots':
            # Use accent color for better visibility on dark backgrounds
            accent_rgb = self._hex_to_rgb_str(self.brand.accent_color)
            return f'''
            .dots-overlay {{
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                background-image: radial-gradient(circle, rgba({accent_rgb}, {0.25 * dec}) 3px, transparent 3px);
                background-size: 30px 30px;
                z-index: 1;
                pointer-events: none;
            }}'''

        elif effect == 'geometric':
            # Use accent color blended for better visibility
            accent_rgb = self._hex_to_rgb_str(self.brand.accent_color)
            return f'''
            .geo-overlay {{
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                background-image:
                    linear-gradient(0deg, rgba({accent_rgb}, {0.15 * dec}) 1px, transparent 1px),
                    linear-gradient(90deg, rgba({accent_rgb}, {0.15 * dec}) 1px, transparent 1px);
                background-size: 50px 50px;
                z-index: 1;
                pointer-events: none;
            }}'''

        return ""

    def _build_og_html(self, width: int = 1200, height: int = 630) -> str:
        """Build HTML for OG image."""
        # Convert colors to RGB for rgba() usage
        accent_rgb = self._hex_to_rgb_str(self.brand.accent_color)
        primary_rgb = self._hex_to_rgb_str(self.brand.primary_color)

        # Tagline - show full text, adjust font size based on length
        tagline_html = ""
        tagline_font_size = 26  # Default
        if self.brand.tagline:
            tagline = self.brand.tagline
            # Reduce font size for longer taglines
            if len(tagline) > 150:
                tagline_font_size = 20
            elif len(tagline) > 100:
                tagline_font_size = 22
            elif len(tagline) > 70:
                tagline_font_size = 24
            tagline_html = f'<p class="tagline">{tagline}</p>'

        # URL-encode font name for Google Fonts
        font_encoded = self.style.font.replace(' ', '+')

        # Calculate decoration-scaled values
        dec = self.style.decoration

        # Get background effect CSS and extra HTML
        bg_effect_css, bg_extra_html = self._get_bg_effect_css(width, height)
        bg_extra_styles = self._get_bg_effect_extra_styles()

        # Determine if we should show blobs (only for aurora, or if explicitly enabled)
        show_corner_blobs = self.style.show_blobs and self.style.bg_effect == 'aurora'

        return f'''<!DOCTYPE html>
<html>
<head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family={font_encoded}:wght@400;700;{self.style.font_weight}&display=swap');

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            width: {width}px;
            height: {height}px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            position: relative;
            overflow: hidden;
            background: {bg_effect_css};
        }}

        {bg_extra_styles}

        /* Content container */
        .content {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 60px 80px;
            z-index: 10;
        }}

        /* Brand name with glow effect */
        .brand-name {{
            color: {self.brand.text_color};
            font-size: 88px;
            font-weight: {self.style.font_weight};
            font-family: '{self.style.font}', -apple-system, BlinkMacSystemFont, sans-serif;
            letter-spacing: -3px;
            line-height: 1.1;
            text-align: center;
            text-shadow:
                0 0 60px rgba({accent_rgb}, {0.4 * self.style.glow if self.style.show_glow else 0}),
                0 0 30px rgba({accent_rgb}, {0.2 * self.style.glow if self.style.show_glow else 0}),
                0 4px 12px rgba(0, 0, 0, {0.4 * self.style.depth});
        }}

        /* Accent line under brand name */
        .accent-line {{
            width: 120px;
            height: 4px;
            margin: 24px 0;
            background: linear-gradient(
                90deg,
                transparent 0%,
                {self.brand.accent_color} 20%,
                {self.brand.accent_color} 80%,
                transparent 100%
            );
            border-radius: 2px;
        }}

        /* Tagline - full text with dynamic font size */
        .tagline {{
            color: {self._blend_colors(self.brand.text_color, self.brand.accent_color, 0.3)};
            font-size: {tagline_font_size}px;
            font-weight: 400;
            line-height: 1.5;
            text-align: center;
            max-width: 900px;
            opacity: 0.85;
        }}

        /* Bottom accent bar */
        .accent-bar {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(
                90deg,
                {self.brand.primary_color} 0%,
                {self.brand.accent_color} 50%,
                {self.brand.primary_color} 100%
            );
        }}

        /* Decorative corner elements */
        .corner {{
            position: absolute;
            border-radius: 50%;
            filter: blur(60px);
            z-index: 1;
        }}

        .corner-1 {{
            width: 300px;
            height: 300px;
            top: -150px;
            right: -50px;
            background: {self.brand.accent_color};
            opacity: {0.15 * dec};
        }}

        .corner-2 {{
            width: 200px;
            height: 200px;
            bottom: -100px;
            left: -50px;
            background: {self.brand.primary_color};
            opacity: {0.12 * dec};
        }}
    </style>
</head>
<body>
    {bg_extra_html}
    {'<div class="corner corner-1"></div><div class="corner corner-2"></div>' if show_corner_blobs else ''}

    <div class="content">
        <h1 class="brand-name">{self.brand.name}</h1>
        {'<div class="accent-line"></div>' if self.style.show_accent_line else ''}
        {tagline_html}
    </div>

    {'<div class="accent-bar"></div>' if self.style.show_bottom_bar else ''}
</body>
</html>'''

    def generate_og_image(self, width: int = 1200, height: int = 630) -> Image.Image:
        """Generate Open Graph image with premium 'Aurora' design.

        Args:
            width: Image width
            height: Image height

        Returns:
            PIL Image (RGB)
        """
        html = self._build_og_html(width, height)
        return self._render_html(html, width, height, transparent=False)

    def _hex_to_rgb_str(self, hex_color: str) -> str:
        """Convert hex color to 'r, g, b' string for CSS rgba()."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"

    def _render_html(
        self,
        html: str,
        width: int,
        height: int,
        transparent: bool = False
    ) -> Image.Image:
        """Render HTML to PIL Image using Playwright.

        Args:
            html: HTML content to render
            width: Viewport width
            height: Viewport height
            transparent: Whether to use transparent background

        Returns:
            PIL Image
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            page = browser.new_page(
                viewport={'width': width, 'height': height},
                device_scale_factor=1,
            )

            page.set_content(html)
            page.wait_for_load_state('networkidle')

            screenshot_bytes = page.screenshot(
                type='png',
                omit_background=transparent,
            )

            browser.close()

        img = Image.open(io.BytesIO(screenshot_bytes))

        if transparent:
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        return img

    def _blend_colors(self, color1: str, color2: str, factor: float) -> str:
        """Blend two hex colors.

        Args:
            color1: Base color (hex)
            color2: Color to blend in (hex)
            factor: Blend factor (0-1)

        Returns:
            Blended color (hex)
        """
        def hex_to_rgb(hex_color: str) -> tuple:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join(c * 2 for c in hex_color)
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        r1, g1, b1 = hex_to_rgb(color1)
        r2, g2, b2 = hex_to_rgb(color2)

        r = int(r1 * (1 - factor) + r2 * factor)
        g = int(g1 * (1 - factor) + g2 * factor)
        b = int(b1 * (1 - factor) + b2 * factor)

        return f'#{r:02x}{g:02x}{b:02x}'
