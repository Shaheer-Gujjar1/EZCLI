#!/usr/bin/env bash
set -e

echo "=== EasyCLI (ezcli) Installer ==="

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "Python 3 is required. Installing python3..."
    sudo apt update && sudo apt install -y python3
fi

# Ensure python3-rich is installed (standard package on Debian/Ubuntu/Deepin)
python3 -c "import rich" 2>/dev/null || {
    echo "Installing python3-rich..."
    sudo apt update && sudo apt install -y python3-rich || pip3 install rich || pip install rich
}

# Ensure emoji font is present
if ! fc-list : family 2>/dev/null | grep -qi "emoji"; then
    echo "Installing fonts-noto-color-emoji..."
    sudo apt install -y fonts-noto-color-emoji || true
fi

# Determine install target directory
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$REPO_DIR/ezcli"

INSTALL_DIR="/usr/local/bin"
if [ -w "$INSTALL_DIR" ]; then
    ln -sf "$REPO_DIR/ezcli" "$INSTALL_DIR/ezcli"
    echo "✅ Successfully linked ezcli to $INSTALL_DIR/ezcli"
else
    echo "Creating symlink in $INSTALL_DIR (requires sudo)..."
    sudo ln -sf "$REPO_DIR/ezcli" "$INSTALL_DIR/ezcli"
    echo "✅ Successfully installed ezcli to $INSTALL_DIR/ezcli"
fi

echo ""
echo "🎉 Installation complete! You can now run 'ezcli' from anywhere."
echo "Try running:"
echo "    ezcli"
echo "    ezcli system-info"
