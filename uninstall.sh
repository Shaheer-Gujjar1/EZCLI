#!/usr/bin/env bash
# ==============================================================================
# EasyCLI (ez) - Uninstaller Entrypoint
# Delegates to the unified Windows-style Setup Wizard (ez-setup.sh)
# ==============================================================================
set -e

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "EasyCLI (ez) Uninstaller"
    echo "Usage: ./uninstall.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -y, --yes          Confirm uninstallation without interactive prompts"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Delegates to the unified EasyCLI Setup Wizard (ez-setup.sh --uninstall)."
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
LOCAL_SETUP="$SCRIPT_DIR/ez-setup.sh"
INSTALLED_SETUP="$HOME/.local/share/ez/ez-setup.sh"

# 1. Local repository setup check
if [ -n "$SCRIPT_DIR" ] && [ -f "$LOCAL_SETUP" ]; then
    chmod +x "$LOCAL_SETUP" 2>/dev/null || true
    exec "$LOCAL_SETUP" --uninstall "$@"
fi

# 2. Installed copy check
if [ -f "$INSTALLED_SETUP" ]; then
    chmod +x "$INSTALLED_SETUP" 2>/dev/null || true
    exec "$INSTALLED_SETUP" --uninstall "$@"
fi

# 3. System PATH check
if command -v ez-setup &>/dev/null; then
    exec "$(command -v ez-setup)" --uninstall "$@"
fi

# 4. Remote standalone fallback
STANDALONE_URL="https://raw.githubusercontent.com/Shaheer-Gujjar1/EZCLI/main/ez-setup.sh"
TMP_DIR="$(mktemp -d /tmp/ezcli-uninstall.XXXXXX)"
TMP_SETUP="$TMP_DIR/ez-setup.sh"

echo "⏳ Fetching EasyCLI uninstallation wizard..."
if command -v curl &>/dev/null; then
    curl -fsSL "$STANDALONE_URL" -o "$TMP_SETUP"
elif command -v wget &>/dev/null; then
    wget -qO "$TMP_SETUP" "$STANDALONE_URL"
fi

if [ -s "$TMP_SETUP" ]; then
    chmod +x "$TMP_SETUP"
    if [ -t 0 ]; then
        "$TMP_SETUP" --uninstall "$@"
    elif [ -e /dev/tty ]; then
        "$TMP_SETUP" --uninstall "$@" < /dev/tty
    else
        "$TMP_SETUP" --uninstall "$@"
    fi
    EXIT_CODE=$?
    rm -rf "$TMP_DIR"
    exit $EXIT_CODE
fi

rm -rf "$TMP_DIR"
echo "❌ Error: Could not find ez-setup.sh to perform uninstallation."
exit 1
