"""Extract color palette from website CSS/HTML."""
import re
from collections import Counter
from typing import List, Dict, Tuple, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from utils.color_utils import (
    normalize_color, luminance, saturation, is_grayscale, color_distance
)


class ColorExtractor:
    """Extract and classify colors from a website."""

    # Common CSS color patterns
    HEX_PATTERN = re.compile(r'#([0-9a-fA-F]{3,6})\b')
    RGB_PATTERN = re.compile(r'rgba?\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+[^)]*\)')
    CSS_VAR_PATTERN = re.compile(r'--[\w-]+:\s*([#\w(),.%\s]+);')

    # Semantic CSS variable patterns (prioritized)
    SEMANTIC_VAR_PATTERNS = {
        'primary': re.compile(r'--(color-)?primary[^:]*:\s*(#[0-9a-fA-F]{3,6})', re.I),
        'accent': re.compile(r'--(color-)?(accent|secondary|highlight)[^:]*:\s*(#[0-9a-fA-F]{3,6})', re.I),
        'background': re.compile(r'--(color-)?(background|bg)[^:]*:\s*(#[0-9a-fA-F]{3,6})', re.I),
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; BrandKitGen/1.0)'
        })

    def extract_from_url(self, url: str) -> Dict[str, any]:
        """Extract all colors from a URL.

        Returns:
            Dict with:
                - colors: List of all unique colors found
                - color_counts: Dict of color -> occurrence count
                - primary: Most likely primary color
                - accent: Most likely accent color
                - background: Most likely background color
                - theme: 'dark' or 'light'
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            html = response.text
        except requests.RequestException as e:
            return {'error': str(e), 'colors': [], 'theme': 'light'}

        soup = BeautifulSoup(html, 'html.parser')

        # Collect all CSS
        all_css = self._collect_css(soup, url)

        # FIRST: Try to extract semantic CSS variables (highest priority)
        semantic_colors = self._extract_semantic_vars(all_css)

        # Extract all colors from CSS
        colors = self._extract_colors(all_css)

        # Also check meta theme-color
        theme_color = self._get_meta_theme_color(soup)
        if theme_color:
            colors.append(theme_color)

        # Count and deduplicate
        color_counts = Counter(colors)
        unique_colors = list(color_counts.keys())

        # Classify colors (fallback if no semantic vars)
        classified = self._classify_colors(unique_colors, color_counts)

        # Override with semantic colors if found
        if semantic_colors.get('primary'):
            classified['primary'] = semantic_colors['primary']
        if semantic_colors.get('accent'):
            classified['accent'] = semantic_colors['accent']
        if semantic_colors.get('background'):
            classified['background'] = semantic_colors['background']
            # Re-determine theme based on actual background
            classified['theme'] = 'dark' if luminance(semantic_colors['background']) < 0.5 else 'light'
            classified['text'] = '#ffffff' if classified['theme'] == 'dark' else '#000000'

        return {
            'colors': unique_colors,
            'color_counts': dict(color_counts),
            'semantic_vars_found': bool(semantic_colors),
            **classified
        }

    def _collect_css(self, soup: BeautifulSoup, base_url: str) -> str:
        """Collect all CSS from inline styles and linked stylesheets."""
        css_parts = []

        # Inline <style> tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                css_parts.append(style_tag.string)

        # Inline style attributes
        for elem in soup.find_all(style=True):
            css_parts.append(elem['style'])

        # Linked stylesheets (first 3 to avoid too many requests)
        for link in soup.find_all('link', rel='stylesheet')[:3]:
            href = link.get('href')
            if href:
                css_url = urljoin(base_url, href)
                try:
                    css_response = self.session.get(css_url, timeout=self.timeout)
                    if css_response.status_code == 200:
                        css_parts.append(css_response.text)
                except requests.RequestException:
                    pass  # Skip failed stylesheet fetches

        return '\n'.join(css_parts)

    def _extract_semantic_vars(self, css: str) -> Dict[str, Optional[str]]:
        """Extract colors from semantic CSS variable names.

        Looks for patterns like:
        - --color-primary: #xxx
        - --primary-color: #xxx
        - --accent: #xxx
        - --background-color: #xxx
        """
        result = {}

        for key, pattern in self.SEMANTIC_VAR_PATTERNS.items():
            match = pattern.search(css)
            if match:
                # Get the last group (the hex color)
                hex_color = match.group(match.lastindex)
                normalized = normalize_color(hex_color)
                if normalized:
                    result[key] = normalized

        return result

    def _extract_colors(self, css: str) -> List[str]:
        """Extract all color values from CSS text."""
        colors = []

        # Extract hex colors
        for match in self.HEX_PATTERN.findall(css):
            normalized = normalize_color(f'#{match}')
            if normalized:
                colors.append(normalized)

        # Extract rgb/rgba colors
        for match in self.RGB_PATTERN.findall(css):
            normalized = normalize_color(match)
            if normalized:
                colors.append(normalized)

        # Extract CSS variable values
        for match in self.CSS_VAR_PATTERN.findall(css):
            value = match.strip()
            normalized = normalize_color(value)
            if normalized:
                colors.append(normalized)

        return colors

    def _get_meta_theme_color(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract theme-color from meta tag."""
        meta = soup.find('meta', attrs={'name': 'theme-color'})
        if meta and meta.get('content'):
            return normalize_color(meta['content'])
        return None

    def _classify_colors(
        self, colors: List[str], counts: Counter
    ) -> Dict[str, str]:
        """Classify colors into primary, accent, background, text.

        Strategy:
        1. Background: darkest or lightest depending on prevalence
        2. Primary: most used non-background, non-grayscale color
        3. Accent: brightest/most saturated color different from primary
        4. Text: white for dark theme, black for light theme
        """
        if not colors:
            return {
                'primary': '#333333',
                'accent': '#666666',
                'background': '#ffffff',
                'text': '#000000',
                'theme': 'light'
            }

        # Sort by luminance
        sorted_by_lum = sorted(colors, key=luminance)

        # Find very dark colors (potential backgrounds for dark theme)
        dark_colors = [c for c in colors if luminance(c) < 0.1]
        light_colors = [c for c in colors if luminance(c) > 0.9]

        # Determine theme based on darkest colors prevalence
        dark_count = sum(counts.get(c, 0) for c in dark_colors)
        light_count = sum(counts.get(c, 0) for c in light_colors)

        is_dark_theme = dark_count > light_count or (dark_colors and not light_colors)

        # Background color
        if is_dark_theme and dark_colors:
            background = min(dark_colors, key=luminance)
        elif light_colors:
            background = max(light_colors, key=luminance)
        else:
            background = sorted_by_lum[-1] if is_dark_theme else sorted_by_lum[0]

        # Find non-background, non-grayscale colors
        chromatic_colors = [
            c for c in colors
            if not is_grayscale(c) and color_distance(c, background) > 50
        ]

        # Primary: most used chromatic color
        if chromatic_colors:
            primary = max(chromatic_colors, key=lambda c: counts.get(c, 0))
        else:
            # Fallback to most common non-background
            non_bg = [c for c in colors if c != background]
            primary = max(non_bg, key=lambda c: counts.get(c, 0)) if non_bg else '#333333'

        # Accent: most saturated color different from primary
        accent_candidates = [
            c for c in chromatic_colors
            if c != primary and color_distance(c, primary) > 30
        ]
        if accent_candidates:
            accent = max(accent_candidates, key=saturation)
        else:
            accent = primary  # Fallback

        # Text color
        text = '#ffffff' if is_dark_theme else '#000000'

        return {
            'primary': primary,
            'accent': accent,
            'background': background,
            'text': text,
            'theme': 'dark' if is_dark_theme else 'light'
        }
