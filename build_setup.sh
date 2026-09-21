#!/usr/bin/env bash
# ==============================================================================
# EasyCLI - Setup Builder
# Packs ezcli_app and ez into a self-extracting standalone ez-setup.sh
# ==============================================================================
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_TEMPLATE="$REPO_DIR/ez-setup-source.sh"
OUTPUT_FILE="$REPO_DIR/ez-setup.sh"

echo "🔨 Building standalone EasyCLI setup manager (ez-setup.sh)..."

if [ ! -f "$SOURCE_TEMPLATE" ]; then
    echo "❌ Error: $SOURCE_TEMPLATE not found."
    exit 1
fi

TMP_DIR="$(mktemp -d /tmp/ezcli-builder.XXXXXX)"
TMP_TAR="$TMP_DIR/ezcli-payload.tar.gz"

echo "📦 Archiving ez and ezcli_app..."
tar --exclude='*__pycache__*' \
    --exclude='*.pyc' \
    --exclude='*.git*' \
    -czf "$TMP_TAR" \
    -C "$REPO_DIR" ez ezcli_app

PAYLOAD_SIZE=$(wc -c < "$TMP_TAR")
echo "   Compressed payload size: $((PAYLOAD_SIZE / 1024)) KB"

echo "📝 Assembling self-extracting script..."
cp "$SOURCE_TEMPLATE" "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "__PAYLOAD_BEGINS__" >> "$OUTPUT_FILE"
base64 "$TMP_TAR" >> "$OUTPUT_FILE"
chmod +x "$OUTPUT_FILE"

# Verify that the generated setup can extract cleanly
echo "🔍 Verifying payload extraction..."
TEST_EXTRACT_DIR="$TMP_DIR/verify"
mkdir -p "$TEST_EXTRACT_DIR"
MARKER_LINE=$(grep -n "^__PAYLOAD_BEGINS__$" "$OUTPUT_FILE" | head -n 1 | cut -d: -f1)
tail -n +"$((MARKER_LINE + 1))" "$OUTPUT_FILE" | base64 -d | tar -xz -C "$TEST_EXTRACT_DIR"

if [ -f "$TEST_EXTRACT_DIR/ez" ] && [ -d "$TEST_EXTRACT_DIR/ezcli_app" ]; then
    echo "✅ Payload verification successful! ez and ezcli_app verified."
else
    echo "❌ Payload verification failed."
    rm -rf "$TMP_DIR"
    exit 1
fi

rm -rf "$TMP_DIR"
TOTAL_SIZE=$(wc -c < "$OUTPUT_FILE")
echo "🎉 Build complete: $OUTPUT_FILE ($((TOTAL_SIZE / 1024)) KB)"
echo "   This single file is 100% standalone and ready for distribution."
