"""Build favicon set from source image."""
import json
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image


# Standard favicon sizes
FAVICON_SIZES = {
    'favicon-16x16.png': 16,
    'favicon-32x32.png': 32,
    'apple-touch-icon.png': 180,
    'android-chrome-192x192.png': 192,
    'android-chrome-512x512.png': 512,
}

# ICO file contains multiple sizes
ICO_SIZES = [16, 32, 48]


class FaviconBuilder:
    """Build complete favicon set from source image."""

    def __init__(self, source_image: Image.Image, theme_color: str = '#000000'):
        """Initialize with source image.

        Args:
            source_image: PIL Image (should be 512x512 for best quality)
            theme_color: Hex color for manifest theme_color
        """
        # Ensure RGBA
        if source_image.mode != 'RGBA':
            source_image = source_image.convert('RGBA')

        self.source = source_image
        self.theme_color = theme_color

    def build_all(self, output_dir: Path, verbose: bool = False) -> Dict[str, Path]:
        """Generate all favicon files.

        Args:
            output_dir: Directory to save files
            verbose: Print progress

        Returns:
            Dict mapping filename to Path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        generated = {}

        # Generate PNG files at each size
        for filename, size in FAVICON_SIZES.items():
            path = output_dir / filename
            resized = self._resize(size)
            resized.save(path, 'PNG', optimize=True)
            generated[filename] = path
            if verbose:
                print(f"  Created {filename} ({size}x{size})")

        # Generate ICO file with multiple sizes
        ico_path = output_dir / 'favicon.ico'
        self._save_ico(ico_path)
        generated['favicon.ico'] = ico_path
        if verbose:
            print(f"  Created favicon.ico ({', '.join(str(s) for s in ICO_SIZES)})")

        # Generate site.webmanifest
        manifest_path = output_dir / 'site.webmanifest'
        self._save_manifest(manifest_path)
        generated['site.webmanifest'] = manifest_path
        if verbose:
            print(f"  Created site.webmanifest")

        return generated

    def _resize(self, size: int) -> Image.Image:
        """Resize source image to target size with high quality."""
        return self.source.resize(
            (size, size),
            resample=Image.Resampling.LANCZOS
        )

    def _save_ico(self, path: Path):
        """Save multi-size ICO file."""
        # Create images at each ICO size
        images = [self._resize(size) for size in ICO_SIZES]

        # Save as ICO
        images[0].save(
            path,
            format='ICO',
            sizes=[(s, s) for s in ICO_SIZES],
            append_images=images[1:]
        )

    def _save_manifest(self, path: Path):
        """Save site.webmanifest file."""
        manifest = {
            "name": "",
            "short_name": "",
            "icons": [
                {
                    "src": "/android-chrome-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/android-chrome-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ],
            "theme_color": self.theme_color,
            "background_color": self.theme_color,
            "display": "standalone"
        }

        with open(path, 'w') as f:
            json.dump(manifest, f, indent=2)


def build_favicon_set(
    source: Image.Image,
    output_dir: Path,
    theme_color: str = '#000000',
    verbose: bool = False
) -> Dict[str, Path]:
    """Convenience function to build favicon set.

    Args:
        source: Source image (512x512 recommended)
        output_dir: Output directory
        theme_color: Theme color for manifest
        verbose: Print progress

    Returns:
        Dict of generated files
    """
    builder = FaviconBuilder(source, theme_color)
    return builder.build_all(output_dir, verbose)
