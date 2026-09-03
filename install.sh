#!/usr/bin/env bash
set -e

echo "=== EasyCLI (ezcli) Installer ==="

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "Python 3 is required. Installing python3..."
    sudo apt update && sudo apt install -y python3
fi

# Ensure python3-rich and python3-textual are installed
python3 -c "import rich" 2>/dev/null || {
    echo "Installing python3-rich..."
    sudo apt update && sudo apt install -y python3-rich || pip3 install rich || pip install rich
}
# Ensure modern textual (>=0.2.0) is available
if ! python3 -c "from textual.widgets import DataTable" 2>/dev/null; then
    echo "Modern Textual not found in system python. Setting up in user environment..."
    mkdir -p "$HOME/.local/share/ezcli"
    if [ ! -d "$HOME/.local/share/ezcli/venv" ]; then
        python3 -m venv "$HOME/.local/share/ezcli/venv" 2>/dev/null || (sudo apt update && sudo apt install -y python3-venv python3-pip && python3 -m venv "$HOME/.local/share/ezcli/venv")
    fi
    if [ -f "$HOME/.local/share/ezcli/venv/bin/pip" ]; then
        "$HOME/.local/share/ezcli/venv/bin/pip" install --upgrade textual rich
    else
        pip3 install --upgrade textual 2>/dev/null || pip install --upgrade textual 2>/dev/null || true
    fi
fi

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
