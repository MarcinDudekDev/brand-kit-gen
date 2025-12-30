#!/usr/bin/env python3
"""Brand Kit Generator - Generate favicon set and OG images from any website URL.

Analyzes a website's CSS to extract brand colors and generates matching
favicon files and Open Graph images.

Usage:
    python brand_kit_gen.py https://example.com --output ./static/
    python brand_kit_gen.py https://example.com --ai --output ./static/
    python brand_kit_gen.py https://example.com --style gradient -v
"""
import argparse
import sys
from pathlib import Path

from extractors.color_extractor import ColorExtractor
from extractors.brand_extractor import BrandExtractor
from generators.pil_generator import PILGenerator
from generators.favicon_builder import build_favicon_set
from generators.ai_generator import AIGenerator
from generators.html_generator import HTMLGenerator, is_playwright_available
from models.brand_identity import BrandIdentity, StyleConfig, MOOD_PRESETS, BG_EFFECTS


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate brand kit (favicons + OG image) from website URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s https://example.com                    # HTML mode (default)
  %(prog)s https://example.com --method pil       # PIL fallback
  %(prog)s https://example.com --ai               # AI generation
  %(prog)s https://example.com --method pil --style gradient

Methods:
  html - HTML/Playwright rendering (default, best quality, FREE)
  pil  - PIL/Pillow fallback (no extra deps)
  ai   - AI providers (may require API keys)

PIL Styles (--method pil):
  minimal   - Clean initials on rounded rectangle
  gradient  - Diagonal gradient with white text
  geometric - Abstract overlapping circles

AI Providers (--ai):
  openai       - Best quality, requires OPENAI_API_KEY
  pollinations - FREE, no API key
  gemini       - Requires GEMINI_API_KEY, geo-restricted
        '''
    )

    parser.add_argument(
        'url',
        help='Website URL to analyze'
    )

    # Default output in script's directory
    script_dir = Path(__file__).parent
    default_output = script_dir / 'output'

    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=default_output,
        help=f'Output directory (default: {default_output})'
    )

    parser.add_argument(
        '--method',
        choices=['html', 'pil', 'ai'],
        default='html',
        help='Generation method: html (Playwright, best), pil (fallback), ai (requires API)'
    )

    parser.add_argument(
        '--ai',
        action='store_true',
        help='Shortcut for --method ai'
    )

    parser.add_argument(
        '--provider',
        choices=['openai', 'pollinations', 'gemini'],
        default=None,
        help='AI provider (default: auto-detect, prefers openai if OPENAI_API_KEY set)'
    )

    parser.add_argument(
        '--style',
        choices=['minimal', 'gradient', 'geometric'],
        default='minimal',
        help='PIL logo style (default: minimal)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    # Manual overrides
    parser.add_argument(
        '--name',
        help='Override brand name'
    )

    parser.add_argument(
        '--primary',
        help='Override primary color (hex)'
    )

    parser.add_argument(
        '--accent',
        help='Override accent color (hex)'
    )

    parser.add_argument(
        '--background',
        help='Override background color (hex)'
    )

    # OG Image styling options (HTML generator only)
    parser.add_argument(
        '--glow', type=float, default=1.0,
        help='Text glow intensity: 0=none, 1=default, 2=strong (HTML only)'
    )
    parser.add_argument(
        '--depth', type=float, default=1.0,
        help='Shadow depth: 0=flat, 1=default, 2=deep (HTML only)'
    )
    parser.add_argument(
        '--decoration', type=float, default=1.0,
        help='Background decoration: 0=none, 1=default, 2=heavy (HTML only)'
    )
    parser.add_argument(
        '--gradient-angle', type=int, default=160,
        help='Background gradient angle in degrees (default: 160)'
    )
    parser.add_argument(
        '--mood', choices=['default', 'minimal', 'bold', 'elegant', 'neon'],
        help='Preset style mood (overrides glow/depth/decoration)'
    )
    parser.add_argument(
        '--no-accent-line', action='store_true',
        help='Hide accent line under brand name'
    )
    parser.add_argument(
        '--no-bottom-bar', action='store_true',
        help='Hide gradient bar at bottom'
    )
    parser.add_argument(
        '--no-blobs', action='store_true',
        help='Hide decorative background blobs'
    )
    parser.add_argument(
        '--no-glow', action='store_true',
        help='Remove all text glow effects'
    )
    parser.add_argument(
        '--font', default='Inter',
        help='Google Font name for brand text (default: Inter)'
    )
    parser.add_argument(
        '--font-weight', type=int, default=800,
        help='Font weight for brand name (default: 800)'
    )
    parser.add_argument(
        '--bg-effect', choices=list(BG_EFFECTS.keys()),
        default='aurora',
        help='Background effect style (default: aurora). Options: ' + ', '.join(BG_EFFECTS.keys())
    )

    return parser.parse_args()


def extract_brand_identity(url: str, args, verbose: bool = False) -> BrandIdentity:
    """Extract brand identity from URL with optional overrides."""
    if verbose:
        print(f"\n📊 Analyzing {url}...")

    # Extract colors
    color_extractor = ColorExtractor()
    color_data = color_extractor.extract_from_url(url)

    if verbose:
        if 'error' in color_data:
            print(f"  ⚠️  Color extraction warning: {color_data['error']}")
        print(f"  Found {len(color_data.get('colors', []))} colors")
        print(f"  Primary: {color_data.get('primary', 'N/A')}")
        print(f"  Accent: {color_data.get('accent', 'N/A')}")
        print(f"  Background: {color_data.get('background', 'N/A')}")
        print(f"  Theme: {color_data.get('theme', 'N/A')}")

    # Extract brand info
    brand_extractor = BrandExtractor()
    brand_data = brand_extractor.extract_from_url(url)

    if verbose:
        if 'error' in brand_data:
            print(f"  ⚠️  Brand extraction warning: {brand_data['error']}")
        print(f"  Name: {brand_data.get('name', 'N/A')}")
        print(f"  Domain: {brand_data.get('domain', 'N/A')}")
        if brand_data.get('tagline'):
            print(f"  Tagline: {brand_data['tagline'][:60]}...")

    # Create BrandIdentity with overrides
    brand = BrandIdentity(
        name=args.name or brand_data.get('name', 'Brand'),
        domain=brand_data.get('domain', ''),
        colors=color_data.get('colors', []),
        primary_color=args.primary or color_data.get('primary', '#333333'),
        accent_color=args.accent or color_data.get('accent', '#666666'),
        background_color=args.background or color_data.get('background', '#ffffff'),
        text_color=color_data.get('text', '#ffffff'),
        theme=color_data.get('theme', 'light'),
        font_family=brand_data.get('font_family'),
        tagline=brand_data.get('tagline'),
    )

    if verbose:
        print(f"\n🎨 Brand Identity:")
        print(f"  {brand}")
        print(f"  Initials: {brand.initials}")

    return brand


def build_style_config(args) -> StyleConfig:
    """Build StyleConfig from CLI arguments."""
    # Start with mood preset or default
    if args.mood:
        style = MOOD_PRESETS[args.mood]
        # Create new instance to avoid modifying preset
        style = StyleConfig(
            glow=style.glow,
            depth=style.depth,
            decoration=style.decoration,
            gradient_angle=style.gradient_angle,
            font=style.font,
            font_weight=style.font_weight,
            show_accent_line=style.show_accent_line,
            show_bottom_bar=style.show_bottom_bar,
            show_blobs=style.show_blobs,
            show_glow=style.show_glow,
            bg_effect=style.bg_effect,
        )
    else:
        style = StyleConfig(
            glow=args.glow,
            depth=args.depth,
            decoration=args.decoration,
            gradient_angle=args.gradient_angle,
            bg_effect=args.bg_effect,
        )

    # Apply explicit overrides (font, toggles)
    style.font = args.font
    style.font_weight = args.font_weight
    style.show_accent_line = not args.no_accent_line
    style.show_bottom_bar = not args.no_bottom_bar
    style.show_blobs = not args.no_blobs
    style.show_glow = not args.no_glow

    # If bg_effect was explicitly set via CLI, override mood preset
    if hasattr(args, 'bg_effect') and args.bg_effect != 'aurora':
        style.bg_effect = args.bg_effect

    return style


def generate_with_html(brand: BrandIdentity, args) -> tuple:
    """Generate logo and OG image using HTML/Playwright."""
    if args.verbose:
        print(f"\n🌐 Generating with HTML/Playwright...")

    style = build_style_config(args)

    if args.verbose and args.mood:
        print(f"   Style mood: {args.mood}")

    generator = HTMLGenerator(brand, style=style)

    logo = generator.generate_logo(size=512)
    og_image = generator.generate_og_image()

    return logo, og_image


def generate_with_pil(brand: BrandIdentity, args) -> tuple:
    """Generate logo and OG image using PIL."""
    if args.verbose:
        print(f"\n🖼️  Generating with PIL (style: {args.style})...")

    generator = PILGenerator(brand)

    logo = generator.generate_logo(size=512, style=args.style)
    og_image = generator.generate_og_image()

    return logo, og_image


def generate_with_ai(brand: BrandIdentity, args) -> tuple:
    """Generate logo and OG image using AI."""
    if args.verbose:
        print(f"\n🤖 Generating with AI...")

    generator = AIGenerator(brand, provider=args.provider)

    logo = generator.generate_logo(size=512)
    og_image = generator.generate_og_image()

    return logo, og_image


def generate_preview_html(output_dir: Path, brand: BrandIdentity, source_url: str, style: StyleConfig = None) -> Path:
    """Generate HTML preview page showing all generated assets with live OG preview."""
    from html import escape
    import json

    # Build effect options HTML
    effect_options = '\n'.join([
        f'<option value="{effect}" {"selected" if style and style.bg_effect == effect else ""}>{escape(effect)} - {escape(desc)}</option>'
        for effect, desc in BG_EFFECTS.items()
    ])

    # Safely encode data for JS
    brand_json = json.dumps({
        'name': brand.name,
        'primary': brand.primary_color,
        'accent': brand.accent_color,
        'background': brand.background_color,
        'text': brand.text_color,
        'tagline': brand.tagline or ''
    })
    effects_json = json.dumps(dict(BG_EFFECTS))
    source_url_json = json.dumps(source_url)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brand Kit Preview - {escape(brand.name)}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <style>
        :root {{ --pico-primary: {brand.primary_color}; --pico-primary-hover: {brand.accent_color}; }}
        body {{ padding: 2rem; }}
        .color-swatch {{ display: inline-flex; flex-direction: column; align-items: center; margin: 0.5rem; }}
        .color-box {{ width: 80px; height: 80px; border-radius: 8px; border: 2px solid #ccc; margin-bottom: 0.5rem; }}
        .favicon-grid {{ display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: end; }}
        .favicon-item {{ text-align: center; }}
        .favicon-item img {{ border: 1px solid #ddd; border-radius: 4px; background: repeating-conic-gradient(#eee 0% 25%, #fff 0% 50%) 50% / 10px 10px; }}
        .og-preview {{ max-width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        code {{ font-size: 0.85em; }}
        .effect-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; margin: 1rem 0; }}
        .effect-card {{ border: 2px solid #ddd; border-radius: 8px; padding: 0.5rem; cursor: pointer; transition: all 0.2s; text-align: center; }}
        .effect-card:hover {{ border-color: var(--pico-primary); transform: translateY(-2px); }}
        .effect-card.active {{ border-color: var(--pico-primary); background: rgba(0,0,0,0.03); }}
        .effect-card h4 {{ margin: 0; font-size: 0.9rem; text-transform: capitalize; }}
        .effect-card p {{ margin: 0.25rem 0 0; font-size: 0.75rem; opacity: 0.7; }}
        .og-frame {{ width: 100%; max-width: 1200px; aspect-ratio: 1200/630; border: none; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .controls {{ display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; align-items: end; }}
        .controls > div {{ flex: 1; min-width: 140px; }}
        .controls label {{ display: block; margin-bottom: 0.25rem; font-size: 0.8rem; }}
        .slider-value {{ min-width: 2rem; text-align: right; }}
        .copy-btn {{ font-size: 0.75rem; padding: 0.2rem 0.5rem; }}
    </style>
</head>
<body>
    <main class="container">
        <header>
            <h1>{escape(brand.name)}</h1>
            <p>Brand kit generated from <a href="{escape(source_url)}" target="_blank">{escape(source_url)}</a></p>
        </header>

        <section>
            <h2>Colors</h2>
            <div>
                <div class="color-swatch"><div class="color-box" style="background: {brand.primary_color};"></div><small>Primary</small><code>{brand.primary_color}</code></div>
                <div class="color-swatch"><div class="color-box" style="background: {brand.accent_color};"></div><small>Accent</small><code>{brand.accent_color}</code></div>
                <div class="color-swatch"><div class="color-box" style="background: {brand.background_color};"></div><small>Background</small><code>{brand.background_color}</code></div>
                <div class="color-swatch"><div class="color-box" style="background: {brand.text_color};"></div><small>Text</small><code>{brand.text_color}</code></div>
            </div>
            <p><small>Theme: <strong>{brand.theme}</strong></small></p>
        </section>

        <section>
            <h2>Logo</h2>
            <p><small>512x512 source image</small></p>
            <img src="android-chrome-512x512.png" width="256" height="256" alt="Logo" style="border-radius: 20%; background: repeating-conic-gradient(#eee 0% 25%, #fff 0% 50%) 50% / 10px 10px;">
        </section>

        <section>
            <h2>Favicons</h2>
            <div class="favicon-grid">
                <div class="favicon-item"><img src="favicon-16x16.png" width="16" height="16" alt="16x16"><br><small>16x16</small></div>
                <div class="favicon-item"><img src="favicon-32x32.png" width="32" height="32" alt="32x32"><br><small>32x32</small></div>
                <div class="favicon-item"><img src="apple-touch-icon.png" width="60" height="60" alt="180x180"><br><small>Apple Touch 180x180</small></div>
                <div class="favicon-item"><img src="android-chrome-192x192.png" width="96" height="96" alt="192x192"><br><small>Android 192x192</small></div>
                <div class="favicon-item"><img src="android-chrome-512x512.png" width="128" height="128" alt="512x512"><br><small>Android HD 512x512</small></div>
            </div>
        </section>

        <section>
            <h2>Open Graph Image (Generated)</h2>
            <p><small>1200x630 - for social media previews</small></p>
            <img src="og-image.png" alt="OG Image" class="og-preview" id="og-static">
        </section>

        <section>
            <h2>Live OG Preview</h2>
            <p><small>Experiment with background effects. Changes are preview only - regenerate to save.</small></p>

            <div class="controls">
                <div><label>Effect</label><select id="bg-effect">{effect_options}</select></div>
                <div><label>Decoration <span class="slider-value" id="dec-val">{style.decoration if style else 1.0}</span></label><input type="range" id="decoration" min="0" max="2" step="0.1" value="{style.decoration if style else 1.0}"></div>
                <div><label>Glow <span class="slider-value" id="glow-val">{style.glow if style else 1.0}</span></label><input type="range" id="glow" min="0" max="2" step="0.1" value="{style.glow if style else 1.0}"></div>
                <div><label>Depth <span class="slider-value" id="depth-val">{style.depth if style else 1.0}</span></label><input type="range" id="depth" min="0" max="2" step="0.1" value="{style.depth if style else 1.0}"></div>
                <div><label>Angle <span class="slider-value" id="angle-val">{style.gradient_angle if style else 160}</span></label><input type="range" id="gradient-angle" min="0" max="360" step="5" value="{style.gradient_angle if style else 160}"></div>
            </div>

            <div class="effect-grid" id="effect-grid"></div>
            <iframe id="og-preview" class="og-frame" srcdoc=""></iframe>
            <p style="margin-top:1rem"><small>Regenerate command:</small><br><code id="regen-cmd"></code> <button class="copy-btn secondary" id="copy-btn">Copy</button></p>
        </section>

        <section>
            <h2>Usage</h2>
            <p>Add to your HTML head:</p>
            <pre><code>&lt;link rel="icon" type="image/x-icon" href="/favicon.ico"&gt;
&lt;link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png"&gt;
&lt;link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png"&gt;
&lt;link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png"&gt;
&lt;link rel="manifest" href="/site.webmanifest"&gt;
&lt;meta name="theme-color" content="{brand.primary_color}"&gt;
&lt;meta property="og:image" content="/og-image.png"&gt;</code></pre>
        </section>
    </main>
    <script>
    const brand = {brand_json};
    const effects = {effects_json};
    const sourceUrl = {source_url_json};

    function hexToRgb(hex) {{
        hex = hex.replace('#', '');
        if (hex.length === 3) hex = hex.split('').map(c => c+c).join('');
        return `${{parseInt(hex.substr(0,2),16)}}, ${{parseInt(hex.substr(2,2),16)}}, ${{parseInt(hex.substr(4,2),16)}}`;
    }}

    function blendColors(c1, c2, factor) {{
        const h2r = h => {{ h = h.replace('#',''); if (h.length===3) h = h.split('').map(c=>c+c).join(''); return [parseInt(h.substr(0,2),16), parseInt(h.substr(2,2),16), parseInt(h.substr(4,2),16)]; }};
        const [r1,g1,b1] = h2r(c1), [r2,g2,b2] = h2r(c2);
        const r = Math.round(r1*(1-factor)+r2*factor), g = Math.round(g1*(1-factor)+g2*factor), b = Math.round(b1*(1-factor)+b2*factor);
        return '#'+[r,g,b].map(x=>x.toString(16).padStart(2,'0')).join('');
    }}

    function getBgCss(effect, dec, angle) {{
        const ar = hexToRgb(brand.accent), pr = hexToRgb(brand.primary), bg = brand.background;
        const map = {{
            'aurora': `radial-gradient(ellipse 700px 500px at 85% 15%, rgba(${{ar}},${{0.35*dec}}) 0%, transparent 70%), radial-gradient(ellipse 500px 400px at 10% 90%, rgba(${{pr}},${{0.25*dec}}) 0%, transparent 70%), radial-gradient(ellipse 800px 400px at 50% 50%, rgba(${{pr}},${{0.08*dec}}) 0%, transparent 60%), linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.15)}})`,
            'mesh': `radial-gradient(ellipse 600px 400px at 20% 20%, rgba(${{ar}},${{0.4*dec}}) 0%, transparent 60%), radial-gradient(ellipse 500px 500px at 80% 30%, rgba(${{pr}},${{0.35*dec}}) 0%, transparent 55%), radial-gradient(ellipse 400px 350px at 60% 70%, rgba(${{ar}},${{0.3*dec}}) 0%, transparent 50%), radial-gradient(ellipse 550px 400px at 10% 80%, rgba(${{pr}},${{0.25*dec}}) 0%, transparent 60%), linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.1)}})`,
            'spotlight': `radial-gradient(ellipse 1000px 800px at 95% 5%, rgba(${{ar}},${{0.5*dec}}) 0%, transparent 50%), radial-gradient(ellipse 600px 600px at 90% 10%, rgba(255,255,255,${{0.15*dec}}) 0%, transparent 40%), linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, '#000', 0.1)}})`,
            'minimal': `linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.08)}})`,
            'diagonal': `linear-gradient(135deg, ${{bg}} 45%, ${{blendColors(brand.primary, bg, 0.5)}} 45%, ${{blendColors(brand.primary, bg, 0.5)}} 55%, ${{blendColors(bg, brand.accent, 0.2)}} 55%)`,
            'noise': `linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.2)}} 50%, ${{blendColors(bg, brand.accent, 0.15)}})`,
            'waves': `linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.1)}})`,
            'glass': `linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.15)}})`,
            'dots': `linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.1)}})`,
            'geometric': `linear-gradient(${{angle}}deg, ${{bg}}, ${{blendColors(bg, brand.primary, 0.08)}})`
        }};
        return map[effect] || map['aurora'];
    }}

    function getExtraHtml(effect, dec) {{
        const ar = hexToRgb(brand.accent), pr = hexToRgb(brand.primary);
        if (effect === 'noise') return '<svg width="0" height="0" style="position:absolute"><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter></svg><div style="position:absolute;inset:0;filter:url(#grain);opacity:'+0.12*dec+';mix-blend-mode:overlay;z-index:2"></div>';
        if (effect === 'waves') {{ const w1 = blendColors(brand.primary, brand.background, 0.7), w2 = blendColors(brand.accent, brand.background, 0.8); return '<svg style="position:absolute;bottom:0;left:0;width:100%;height:100%;z-index:1" viewBox="0 0 1200 630" preserveAspectRatio="none"><path d="M0,500 C200,450 400,550 600,480 C800,410 1000,520 1200,470 L1200,630 L0,630 Z" fill="'+w1+'" opacity="'+0.4*dec+'"/><path d="M0,530 C300,480 500,580 700,510 C900,440 1100,550 1200,500 L1200,630 L0,630 Z" fill="'+w2+'" opacity="'+0.3*dec+'"/><path d="M0,560 C250,520 450,600 650,550 C850,500 1050,580 1200,540 L1200,630 L0,630 Z" fill="'+brand.primary+'" opacity="'+0.2*dec+'"/></svg>'; }}
        if (effect === 'glass') return '<div style="position:absolute;border-radius:50%;background:linear-gradient(135deg,rgba('+ar+','+0.3*dec+'),rgba('+pr+','+0.1*dec+'));filter:blur(40px);z-index:1;width:400px;height:400px;top:-100px;right:-50px"></div><div style="position:absolute;border-radius:50%;background:linear-gradient(135deg,rgba('+pr+','+0.25*dec+'),rgba('+ar+','+0.1*dec+'));filter:blur(40px);z-index:1;width:300px;height:300px;bottom:-80px;left:-60px"></div><div style="position:absolute;border-radius:50%;background:rgba(255,255,255,'+0.1*dec+');filter:blur(60px);z-index:1;width:200px;height:200px;top:40%;left:30%"></div>';
        if (effect === 'dots') return '<div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba('+pr+','+0.15*dec+') 1.5px,transparent 1.5px);background-size:24px 24px;z-index:1"></div>';
        if (effect === 'geometric') {{ const lc = blendColors(brand.primary, brand.background, 0.9); return '<div style="position:absolute;inset:0;background-image:linear-gradient(0deg,'+lc+' 1px,transparent 1px),linear-gradient(90deg,'+lc+' 1px,transparent 1px);background-size:60px 60px;z-index:1;opacity:'+0.5*dec+'"></div>'; }}
        return '';
    }}

    function genHtml(effect, dec, glow, depth, angle) {{
        const ar = hexToRgb(brand.accent), bgCss = getBgCss(effect, dec, angle), extra = getExtraHtml(effect, dec);
        const tagline = brand.tagline ? '<p style="color:'+blendColors(brand.text, brand.accent, 0.3)+';font-size:26px;text-align:center;max-width:900px;opacity:0.85">'+brand.tagline+'</p>' : '';
        return '<!DOCTYPE html><html><head><style>@import url("https://fonts.googleapis.com/css2?family=Inter:wght@800&display=swap");*{{margin:0;padding:0;box-sizing:border-box}}body{{width:1200px;height:630px;font-family:Inter,sans-serif;position:relative;overflow:hidden;background:'+bgCss+'}}.content{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:60px 80px;z-index:10}}.brand-name{{color:'+brand.text+';font-size:88px;font-weight:800;letter-spacing:-3px;text-align:center;text-shadow:0 0 60px rgba('+ar+','+0.4*glow+'),0 0 30px rgba('+ar+','+0.2*glow+'),0 4px 12px rgba(0,0,0,'+0.4*depth+')}}.accent-line{{width:120px;height:4px;margin:24px 0;background:linear-gradient(90deg,transparent,'+brand.accent+' 20%,'+brand.accent+' 80%,transparent);border-radius:2px}}.accent-bar{{position:absolute;bottom:0;left:0;right:0;height:6px;background:linear-gradient(90deg,'+brand.primary+','+brand.accent+','+brand.primary+')}}</style></head><body>'+extra+'<div class="content"><h1 class="brand-name">'+brand.name+'</h1><div class="accent-line"></div>'+tagline+'</div><div class="accent-bar"></div></body></html>';
    }}

    function update() {{
        const effect = document.getElementById('bg-effect').value;
        const dec = parseFloat(document.getElementById('decoration').value);
        const glow = parseFloat(document.getElementById('glow').value);
        const depth = parseFloat(document.getElementById('depth').value);
        const angle = parseInt(document.getElementById('gradient-angle').value);
        document.getElementById('dec-val').textContent = dec.toFixed(1);
        document.getElementById('glow-val').textContent = glow.toFixed(1);
        document.getElementById('depth-val').textContent = depth.toFixed(1);
        document.getElementById('angle-val').textContent = angle;
        document.querySelectorAll('.effect-card').forEach(c => c.classList.toggle('active', c.dataset.effect === effect));
        document.getElementById('og-preview').srcdoc = genHtml(effect, dec, glow, depth, angle);
        let cmd = 'python brand_kit_gen.py ' + sourceUrl + ' --bg-effect ' + effect;
        if (dec !== 1.0) cmd += ' --decoration ' + dec;
        if (glow !== 1.0) cmd += ' --glow ' + glow;
        if (depth !== 1.0) cmd += ' --depth ' + depth;
        if (angle !== 160) cmd += ' --gradient-angle ' + angle;
        document.getElementById('regen-cmd').textContent = cmd;
    }}

    const grid = document.getElementById('effect-grid');
    for (const [e, d] of Object.entries(effects)) {{
        const card = document.createElement('div');
        card.className = 'effect-card';
        card.dataset.effect = e;
        const h4 = document.createElement('h4');
        h4.textContent = e;
        const p = document.createElement('p');
        p.textContent = d;
        card.appendChild(h4);
        card.appendChild(p);
        card.onclick = () => {{ document.getElementById('bg-effect').value = e; update(); }};
        grid.appendChild(card);
    }}

    ['bg-effect','decoration','glow','depth','gradient-angle'].forEach(id => document.getElementById(id).addEventListener('input', update));
    document.getElementById('copy-btn').onclick = () => navigator.clipboard.writeText(document.getElementById('regen-cmd').textContent);
    update();
    </script>
</body>
</html>'''

    preview_path = output_dir / 'preview.html'
    preview_path.write_text(html)
    return preview_path


def main():
    args = parse_args()

    try:
        # Extract brand identity
        brand = extract_brand_identity(args.url, args, verbose=args.verbose)

        # Determine generation method
        method = args.method
        if args.ai:
            method = 'ai'

        # Check if HTML/Playwright is available, fallback to PIL if not
        if method == 'html' and not is_playwright_available():
            if args.verbose:
                print("\n⚠️  Playwright not available, falling back to PIL")
                print("   To enable HTML mode: pip install playwright && playwright install chromium")
            method = 'pil'

        # Build style config for HTML method
        style = build_style_config(args) if method == 'html' else None

        # Generate images
        if method == 'html':
            logo, og_image = generate_with_html(brand, args)
        elif method == 'ai':
            logo, og_image = generate_with_ai(brand, args)
        else:
            logo, og_image = generate_with_pil(brand, args)

        # Build favicon set
        if args.verbose:
            print(f"\n📁 Building favicon set in {args.output}/...")

        args.output.mkdir(parents=True, exist_ok=True)

        generated = build_favicon_set(
            source=logo,
            output_dir=args.output,
            theme_color=brand.primary_color,
            verbose=args.verbose
        )

        # Save OG image
        og_path = args.output / 'og-image.png'
        og_image.save(og_path, 'PNG', optimize=True)
        if args.verbose:
            print(f"  Created og-image.png (1200x630)")

        # Generate HTML preview with style info for live preview
        preview_path = generate_preview_html(args.output, brand, args.url, style)
        if args.verbose:
            print(f"  Created preview.html")

        # Summary
        print(f"\n✅ Brand kit generated successfully!")
        print(f"   Output: {args.output.absolute()}")
        print(f"   Files: {len(generated) + 2} total")
        print(f"\n   Colors used:")
        print(f"     Primary:    {brand.primary_color}")
        print(f"     Accent:     {brand.accent_color}")
        print(f"     Background: {brand.background_color}")
        print(f"\n   📄 Preview: file://{preview_path.absolute()}")

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
