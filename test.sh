#!/bin/bash
# Brand Kit Generator - Test Script

set -e

echo "🧪 Brand Kit Generator - Test Suite"
echo "===================================="

# Activate venv
source .venv/bin/activate

# Test URL
TEST_URL="${1:-https://example.com}"
OUTPUT_DIR="/tmp/brand-kit-test-$$"

echo "📍 Testing with: $TEST_URL"
echo "📁 Output: $OUTPUT_DIR"
echo ""

# Test CLI with default effect
echo "1️⃣  Testing CLI (aurora effect)..."
python brand_kit_gen.py "$TEST_URL" -o "$OUTPUT_DIR/aurora" -v

# Test a few different effects
for effect in spotlight dots geometric; do
    echo ""
    echo "2️⃣  Testing --bg-effect $effect..."
    python brand_kit_gen.py "$TEST_URL" --bg-effect "$effect" -o "$OUTPUT_DIR/$effect"
done

# Check output files exist
echo ""
echo "📋 Checking generated files..."
EXPECTED_FILES="favicon.ico favicon-16x16.png favicon-32x32.png apple-touch-icon.png android-chrome-192x192.png android-chrome-512x512.png og-image.png site.webmanifest preview.html"

for file in $EXPECTED_FILES; do
    if [ -f "$OUTPUT_DIR/aurora/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file MISSING"
        exit 1
    fi
done

# Test web server starts
echo ""
echo "3️⃣  Testing web server..."
python app.py &
SERVER_PID=$!
sleep 3

if curl -s http://localhost:8000 > /dev/null; then
    echo "  ✓ Web server responds"
else
    echo "  ✗ Web server failed to start"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

# Test API endpoint
if curl -s "http://localhost:8000/effects" | grep -q "aurora"; then
    echo "  ✓ API /effects endpoint works"
else
    echo "  ✗ API endpoint failed"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

kill $SERVER_PID 2>/dev/null

echo ""
echo "✅ All tests passed!"
echo ""
echo "Test output saved to: $OUTPUT_DIR"
echo "Open preview: open $OUTPUT_DIR/aurora/preview.html"
