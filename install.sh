#!/bin/bash
# Brand Kit Generator - Installation Script

set -e

echo "🎨 Brand Kit Generator - Installation"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Install Playwright browser
echo "🌐 Installing Playwright Chromium..."
playwright install chromium

echo ""
echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  source .venv/bin/activate"
echo "  python brand_kit_gen.py https://example.com"
echo ""
echo "Or start the web UI:"
echo "  python app.py"
echo "  # Open http://localhost:8000"
