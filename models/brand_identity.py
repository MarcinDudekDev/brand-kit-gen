"""Brand identity dataclass for storing extracted brand information."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StyleConfig:
    """Style configuration for OG image generation."""
    glow: float = 1.0           # Text glow intensity (0=none, 2=strong)
    depth: float = 1.0          # Shadow depth (0=flat, 2=deep)
    decoration: float = 1.0     # Background blobs intensity (0=none)
    gradient_angle: int = 160   # Background gradient angle in degrees
    font: str = "Inter"         # Google Font name
    font_weight: int = 800      # Font weight for brand name
    show_accent_line: bool = True
    show_bottom_bar: bool = True
    show_blobs: bool = True
    show_glow: bool = True
    bg_effect: str = "aurora"   # Background effect type


# Available background effects
BG_EFFECTS = {
    'aurora': 'Smooth radial gradient blobs (default)',
    'mesh': 'Multi-point mesh gradient blend',
    'noise': 'Grainy textured gradient',
    'waves': 'Layered SVG wave curves',
    'spotlight': 'Dramatic corner lighting',
    'minimal': 'Clean simple gradient',
    'glass': 'Glassmorphism with blur',
    'dots': 'Subtle dot pattern overlay',
    'diagonal': 'Bold diagonal color split',
    'geometric': 'Subtle geometric grid pattern',
}


# Preset moods
MOOD_PRESETS = {
    'default': StyleConfig(),
    'minimal': StyleConfig(glow=0.2, depth=0.3, decoration=0.3, bg_effect='minimal'),
    'bold': StyleConfig(glow=1.5, depth=1.3, decoration=1.2, bg_effect='spotlight'),
    'elegant': StyleConfig(glow=0.6, depth=0.5, decoration=0.8, bg_effect='mesh'),
    'neon': StyleConfig(glow=2.0, depth=0.8, decoration=1.5, bg_effect='aurora'),
}


@dataclass
class BrandIdentity:
    """Represents extracted brand identity from a website."""

    name: str                              # "FairPrice"
    domain: str                            # "fairprice.work"
    colors: List[str] = field(default_factory=list)  # All extracted colors
    primary_color: str = "#333333"         # Main brand color
    accent_color: str = "#666666"          # Secondary/highlight color
    background_color: str = "#ffffff"      # Background color
    text_color: str = "#000000"            # Text color for contrast
    theme: str = "light"                   # "dark" or "light"
    font_family: Optional[str] = None      # "Helvetica, sans-serif"
    tagline: Optional[str] = None          # Optional tagline/description

    @property
    def initials(self) -> str:
        """Get brand initials for text logo (e.g., 'FP' for 'FairPrice')."""
        import re

        # Clean the name
        clean_name = ''.join(c for c in self.name if c.isalnum() or c.isspace())

        # First try: split by spaces
        words = clean_name.split()
        if len(words) >= 2:
            return (words[0][0] + words[-1][0]).upper()

        # Second try: split CamelCase (FairPrice -> Fair, Price)
        camel_words = re.findall(r'[A-Z][a-z]*', clean_name)
        if len(camel_words) >= 2:
            return (camel_words[0][0] + camel_words[-1][0]).upper()

        # Fallback: first two characters
        if len(clean_name) >= 2:
            return clean_name[:2].upper()

        return clean_name.upper() or "??"

    def __repr__(self) -> str:
        return (
            f"BrandIdentity(name='{self.name}', domain='{self.domain}', "
            f"primary='{self.primary_color}', accent='{self.accent_color}', "
            f"theme='{self.theme}')"
        )
