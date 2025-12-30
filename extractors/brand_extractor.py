"""Extract brand name and metadata from website."""
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class BrandExtractor:
    """Extract brand name, font, and other metadata from a website."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; BrandKitGen/1.0)'
        })

    def extract_from_url(self, url: str) -> dict:
        """Extract brand info from URL.

        Returns:
            Dict with:
                - name: Brand name
                - domain: Domain name
                - tagline: Optional tagline/description
                - font_family: Detected font
        """
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            html = response.text
        except requests.RequestException as e:
            # Fallback to domain-based name
            name = self._domain_to_name(domain)
            return {
                'name': name,
                'domain': domain,
                'tagline': None,
                'font_family': None,
                'error': str(e)
            }

        soup = BeautifulSoup(html, 'html.parser')

        name = self._extract_name(soup, domain)
        tagline = self._extract_tagline(soup)
        font_family = self._extract_font(soup)

        return {
            'name': name,
            'domain': domain,
            'tagline': tagline,
            'font_family': font_family
        }

    def _extract_name(self, soup: BeautifulSoup, domain: str) -> str:
        """Extract brand name from various sources."""
        # Priority order:
        # 1. og:site_name
        # 2. title tag (cleaned)
        # 3. h1 tag
        # 4. Domain name

        # Check og:site_name
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            return og_site['content'].strip()

        # Check title tag
        title = soup.find('title')
        if title and title.string:
            name = self._clean_title(title.string)
            if name:
                return name

        # Check first h1
        h1 = soup.find('h1')
        if h1:
            text = h1.get_text(strip=True)
            if text and len(text) < 50:
                return text

        # Fallback to domain
        return self._domain_to_name(domain)

    def _clean_title(self, title: str) -> str:
        """Clean page title to extract brand name.

        Removes common patterns like:
        - "Home | Brand Name"
        - "Brand Name - Description"
        - "Brand Name | Tagline"
        """
        title = title.strip()

        # Split by common separators
        separators = [' | ', ' - ', ' — ', ' :: ', ' : ']
        parts = [title]

        for sep in separators:
            if sep in title:
                parts = title.split(sep)
                break

        # Take the shortest meaningful part (likely the brand name)
        candidates = [p.strip() for p in parts if len(p.strip()) > 1]

        if not candidates:
            return title

        # Prefer parts that don't start with common generic words
        generic_starters = ['home', 'welcome', 'the', 'official', 'my']
        for part in candidates:
            if not any(part.lower().startswith(g) for g in generic_starters):
                return part

        return candidates[0]

    def _domain_to_name(self, domain: str) -> str:
        """Convert domain to readable name.

        'fairprice.work' -> 'FairPrice'
        'my-cool-site.com' -> 'My Cool Site'
        """
        # Remove TLD
        name = domain.split('.')[0]

        # Handle hyphens
        if '-' in name:
            words = name.split('-')
            return ' '.join(w.capitalize() for w in words)

        # Handle camelCase or run-together words
        # Simple approach: just capitalize first letter
        # Could use word segmentation but keeping it simple

        # Check for obvious word boundaries (uppercase in middle)
        if any(c.isupper() for c in name[1:]):
            # Already has some casing, preserve it
            return name[0].upper() + name[1:]

        return name.capitalize()

    def _extract_tagline(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract tagline from meta description or og:description."""
        # Try og:description first
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            desc = og_desc['content'].strip()
            if len(desc) < 200:
                return desc

        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc['content'].strip()
            if len(desc) < 200:
                return desc

        return None

    def _extract_font(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract primary font family from CSS."""
        # Check inline styles on body
        body = soup.find('body')
        if body and body.get('style'):
            font = self._parse_font_from_style(body['style'])
            if font:
                return font

        # Check style tags for body/html font-family
        for style in soup.find_all('style'):
            if style.string:
                font = self._parse_font_from_css(style.string)
                if font:
                    return font

        return None

    def _parse_font_from_style(self, style: str) -> Optional[str]:
        """Parse font-family from inline style."""
        match = re.search(r'font-family:\s*([^;]+)', style, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip('"\'')
        return None

    def _parse_font_from_css(self, css: str) -> Optional[str]:
        """Parse font-family from CSS targeting body/html."""
        # Look for body { ... font-family: ... }
        body_match = re.search(
            r'(?:body|html)\s*\{[^}]*font-family:\s*([^;]+)',
            css,
            re.IGNORECASE | re.DOTALL
        )
        if body_match:
            return body_match.group(1).strip().strip('"\'')

        # Look for :root CSS variable
        root_match = re.search(
            r'--font-(?:family|primary|main):\s*([^;]+)',
            css,
            re.IGNORECASE
        )
        if root_match:
            return root_match.group(1).strip().strip('"\'')

        return None
