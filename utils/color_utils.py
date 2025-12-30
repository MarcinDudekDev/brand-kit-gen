"""Color utility functions for brand-kit-gen."""
import re
from typing import Tuple, Optional


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple.

    Args:
        hex_color: Color in #RGB or #RRGGBB format

    Returns:
        Tuple of (R, G, B) values 0-255
    """
    hex_color = hex_color.lstrip('#')

    # Handle 3-char shorthand (#FFF -> #FFFFFF)
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)

    if len(hex_color) != 6:
        return (0, 0, 0)

    try:
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    except ValueError:
        return (0, 0, 0)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def luminance(hex_color: str) -> float:
    """Calculate relative luminance of a color (0-1 scale).

    Uses WCAG formula for perceptual brightness.
    Dark colors < 0.5, light colors > 0.5
    """
    r, g, b = hex_to_rgb(hex_color)

    # Normalize to 0-1
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # Apply gamma correction
    def gamma(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = gamma(r_norm)
    g_lin = gamma(g_norm)
    b_lin = gamma(b_norm)

    # WCAG relative luminance
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color1: str, color2: str) -> float:
    """Calculate contrast ratio between two colors (1-21 scale).

    WCAG requires 4.5:1 for normal text, 3:1 for large text.
    """
    l1 = luminance(color1)
    l2 = luminance(color2)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)


def is_dark_theme(background_color: str) -> bool:
    """Determine if a background color indicates dark theme."""
    return luminance(background_color) < 0.5


def get_text_color(background_color: str) -> str:
    """Get appropriate text color (white or black) for given background."""
    return "#ffffff" if is_dark_theme(background_color) else "#000000"


def parse_rgb_string(rgb_str: str) -> Optional[str]:
    """Parse rgb(r, g, b) or rgba(r, g, b, a) to hex.

    Args:
        rgb_str: String like 'rgb(255, 128, 0)' or 'rgba(255, 128, 0, 0.5)'

    Returns:
        Hex color string or None if invalid
    """
    # Match rgb(r, g, b) or rgba(r, g, b, a)
    pattern = r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)'
    match = re.search(pattern, rgb_str)

    if match:
        r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return rgb_to_hex(r, g, b)

    return None


def normalize_color(color: str) -> Optional[str]:
    """Normalize any color format to lowercase hex.

    Handles: #RGB, #RRGGBB, rgb(), rgba()
    """
    color = color.strip().lower()

    if color.startswith('#'):
        hex_color = color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)
        if len(hex_color) == 6 and all(c in '0123456789abcdef' for c in hex_color):
            return f"#{hex_color}"
    elif color.startswith('rgb'):
        return parse_rgb_string(color)

    return None


def color_distance(color1: str, color2: str) -> float:
    """Calculate Euclidean distance between two colors in RGB space."""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


def is_grayscale(hex_color: str, tolerance: int = 10) -> bool:
    """Check if color is grayscale (R ≈ G ≈ B)."""
    r, g, b = hex_to_rgb(hex_color)
    return max(r, g, b) - min(r, g, b) <= tolerance


def saturation(hex_color: str) -> float:
    """Calculate color saturation (0-1 scale)."""
    r, g, b = hex_to_rgb(hex_color)
    max_c = max(r, g, b)
    min_c = min(r, g, b)

    if max_c == 0:
        return 0.0

    return (max_c - min_c) / max_c
