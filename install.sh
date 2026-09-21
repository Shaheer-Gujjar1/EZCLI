#!/usr/bin/env bash
# ==============================================================================
# EasyCLI (ez) - Online 1-Command Loader & Setup Wizard Entrypoint
# Downloads and executes the self-contained standalone ez-setup.sh (no git clone)
# ==============================================================================
set -e

REPO_SLUG="Shaheer-Gujjar1/EZCLI"
STANDALONE_URL="https://raw.githubusercontent.com/${REPO_SLUG}/main/ez-setup.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
LOCAL_SETUP="$SCRIPT_DIR/ez-setup.sh"

# 1. Local execution check: If already inside cloned repo with ez-setup.sh present
if [ -n "$SCRIPT_DIR" ] && [ -f "$LOCAL_SETUP" ]; then
    chmod +x "$LOCAL_SETUP" 2>/dev/null || true
    exec "$LOCAL_SETUP" "$@"
fi

# 2. Remote 1-command execution: Download standalone ez-setup.sh only
TMP_DIR="$(mktemp -d /tmp/ezcli-setup.XXXXXX)"
TMP_SETUP="$TMP_DIR/ez-setup.sh"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                  EasyCLI (ez) - Standalone Setup Loader                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⏳ Downloading self-contained standalone setup manager (ez-setup.sh)..."

DOWNLOADED=false
if command -v curl &>/dev/null; then
    curl -fsSL "$STANDALONE_URL" -o "$TMP_SETUP" && DOWNLOADED=true
elif command -v wget &>/dev/null; then
    wget -qO "$TMP_SETUP" "$STANDALONE_URL" && DOWNLOADED=true
else
    echo "❌ Error: Neither 'curl' nor 'wget' is available on this system."
    echo "   Please install curl or wget to continue."
    rm -rf "$TMP_DIR"
    exit 1
fi

if [ "$DOWNLOADED" != true ] || [ ! -s "$TMP_SETUP" ]; then
    echo "❌ Error: Failed to download ez-setup.sh from GitHub."
    rm -rf "$TMP_DIR"
    exit 1
fi

chmod +x "$TMP_SETUP"
echo "✅ Standalone setup manager downloaded successfully."
echo "🚀 Launching EasyCLI Setup Wizard..."
echo ""

# Reconnect stdin to controlling tty so interactive TUI works even when piped via curl | bash
if [ -t 0 ]; then
    "$TMP_SETUP" "$@"
    EXIT_CODE=$?
elif [ -e /dev/tty ]; then
    "$TMP_SETUP" "$@" < /dev/tty
    EXIT_CODE=$?
else
    "$TMP_SETUP" --install "$@"
    EXIT_CODE=$?
fi

rm -rf "$TMP_DIR"
exit $EXIT_CODE
