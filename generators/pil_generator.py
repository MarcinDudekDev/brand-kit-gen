"""PIL-based logo and OG image generator."""
import math
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from models.brand_identity import BrandIdentity
from utils.color_utils import hex_to_rgb


# Font paths on macOS
FONT_PATHS = [
    '/System/Library/Fonts/Helvetica.ttc',
    '/System/Library/Fonts/SFNSMono.ttf',
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    '/System/Library/Fonts/Supplemental/Arial.ttf',
]


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Get a font at specified size, with fallback."""
    for font_path in FONT_PATHS:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                continue
    # Fallback to default
    return ImageFont.load_default()


class PILGenerator:
    """Generate logos and OG images using PIL."""

    def __init__(self, brand: BrandIdentity):
        self.brand = brand
        self.primary_rgb = hex_to_rgb(brand.primary_color)
        self.accent_rgb = hex_to_rgb(brand.accent_color)
        self.bg_rgb = hex_to_rgb(brand.background_color)
        self.text_rgb = hex_to_rgb(brand.text_color)

    def generate_logo(self, size: int = 512, style: str = 'minimal') -> Image.Image:
        """Generate a logo image.

        Args:
            size: Image size (square)
            style: 'minimal', 'gradient', or 'geometric'

        Returns:
            PIL Image (RGBA)
        """
        if style == 'gradient':
            return self._generate_gradient_logo(size)
        elif style == 'geometric':
            return self._generate_geometric_logo(size)
        else:
            return self._generate_minimal_logo(size)

    def _generate_minimal_logo(self, size: int) -> Image.Image:
        """Minimal style: initials on rounded rectangle background."""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw rounded rectangle background
        padding = size // 10
        corner_radius = size // 5

        # Background shape
        self._draw_rounded_rect(
            draw,
            (padding, padding, size - padding, size - padding),
            corner_radius,
            fill=self.primary_rgb
        )

        # Draw initials
        initials = self.brand.initials
        font_size = int(size * 0.45)
        font = get_font(font_size)

        # Center text
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size - text_width) // 2
        y = (size - text_height) // 2 - bbox[1]  # Adjust for font baseline

        # Use accent color for text if it contrasts well, otherwise use text_color
        text_color = self.accent_rgb if self._contrast_ok() else self.text_rgb
        draw.text((x, y), initials, font=font, fill=text_color)

        return img

    def _generate_gradient_logo(self, size: int) -> Image.Image:
        """Gradient style: diagonal gradient with white text."""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))

        # Create gradient
        for y in range(size):
            for x in range(size):
                # Diagonal gradient factor
                factor = (x + y) / (2 * size)
                r = int(self.primary_rgb[0] * (1 - factor) + self.accent_rgb[0] * factor)
                g = int(self.primary_rgb[1] * (1 - factor) + self.accent_rgb[1] * factor)
                b = int(self.primary_rgb[2] * (1 - factor) + self.accent_rgb[2] * factor)
                img.putpixel((x, y), (r, g, b, 255))

        # Draw white initials
        draw = ImageDraw.Draw(img)
        initials = self.brand.initials
        font_size = int(size * 0.45)
        font = get_font(font_size)

        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size - text_width) // 2
        y = (size - text_height) // 2 - bbox[1]

        draw.text((x, y), initials, font=font, fill=(255, 255, 255, 255))

        return img

    def _generate_geometric_logo(self, size: int) -> Image.Image:
        """Geometric style: overlapping circles."""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        center = size // 2
        radius = size // 3

        # Draw overlapping circles
        offsets = [
            (-radius // 2, 0),
            (radius // 2, 0),
            (0, -radius // 2),
        ]

        colors = [
            (*self.primary_rgb, 180),
            (*self.accent_rgb, 180),
            (*self.bg_rgb, 180) if sum(self.bg_rgb) > 100 else (*self.primary_rgb, 100),
        ]

        for (ox, oy), color in zip(offsets, colors):
            x0 = center + ox - radius
            y0 = center + oy - radius
            x1 = center + ox + radius
            y1 = center + oy + radius
            draw.ellipse([x0, y0, x1, y1], fill=color)

        return img

    def generate_og_image(self, width: int = 1200, height: int = 630) -> Image.Image:
        """Generate Open Graph image for social media.

        Creates a gradient background with centered brand name.
        """
        img = Image.new('RGB', (width, height), self.bg_rgb)

        # Add subtle gradient overlay
        for y in range(height):
            factor = y / height
            for x in range(width):
                current = img.getpixel((x, y))
                # Blend towards accent at bottom
                r = int(current[0] * (1 - factor * 0.3) + self.accent_rgb[0] * factor * 0.3)
                g = int(current[1] * (1 - factor * 0.3) + self.accent_rgb[1] * factor * 0.3)
                b = int(current[2] * (1 - factor * 0.3) + self.accent_rgb[2] * factor * 0.3)
                img.putpixel((x, y), (r, g, b))

        draw = ImageDraw.Draw(img)

        # Draw brand name
        font_size = height // 5
        font = get_font(font_size)

        text = self.brand.name
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (width - text_width) // 2
        y = (height - text_height) // 2 - bbox[1] - 30  # Slightly above center

        draw.text((x, y), text, font=font, fill=self.text_rgb)

        # Draw tagline if available
        if self.brand.tagline:
            tagline_font_size = height // 15
            tagline_font = get_font(tagline_font_size)
            tagline = self.brand.tagline[:80]  # Truncate long taglines

            t_bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
            t_width = t_bbox[2] - t_bbox[0]

            tx = (width - t_width) // 2
            ty = y + text_height + 40

            # Slightly transparent text color
            tagline_color = (*self.text_rgb, 200) if len(self.text_rgb) == 3 else self.text_rgb
            draw.text((tx, ty), tagline, font=tagline_font, fill=tagline_color[:3])

        # Add accent bar at bottom
        bar_height = 8
        draw.rectangle(
            [0, height - bar_height, width, height],
            fill=self.accent_rgb
        )

        return img

    def _draw_rounded_rect(
        self,
        draw: ImageDraw.Draw,
        bounds: Tuple[int, int, int, int],
        radius: int,
        fill: Tuple[int, ...]
    ):
        """Draw a rounded rectangle."""
        x0, y0, x1, y1 = bounds

        # PIL 9.2+ has rounded_rectangle
        try:
            draw.rounded_rectangle(bounds, radius, fill=fill)
        except AttributeError:
            # Fallback for older PIL
            draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
            draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
            draw.ellipse([x0, y0, x0 + 2*radius, y0 + 2*radius], fill=fill)
            draw.ellipse([x1 - 2*radius, y0, x1, y0 + 2*radius], fill=fill)
            draw.ellipse([x0, y1 - 2*radius, x0 + 2*radius, y1], fill=fill)
            draw.ellipse([x1 - 2*radius, y1 - 2*radius, x1, y1], fill=fill)

    def _contrast_ok(self) -> bool:
        """Check if accent color has enough contrast with primary."""
        # Simple luminance difference check
        primary_lum = sum(self.primary_rgb) / 3
        accent_lum = sum(self.accent_rgb) / 3
        return abs(primary_lum - accent_lum) > 80
