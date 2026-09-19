#!/usr/bin/env bash
set -e

echo "=== EasyCLI (ez) Installer ==="

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
    mkdir -p "$HOME/.local/share/ez"
    if [ ! -d "$HOME/.local/share/ez/venv" ]; then
        python3 -m venv "$HOME/.local/share/ez/venv" 2>/dev/null || (sudo apt update && sudo apt install -y python3-venv python3-pip && python3 -m venv "$HOME/.local/share/ez/venv")
    fi
    if [ -f "$HOME/.local/share/ez/venv/bin/pip" ]; then
        "$HOME/.local/share/ez/venv/bin/pip" install --upgrade textual rich
    else
        pip3 install --upgrade textual 2>/dev/null || pip install --upgrade textual 2>/dev/null || true
    fi
fi

# ==============================================================================
# Emoji Font Detection & Priority Setup
# ==============================================================================
echo ""
echo "🔍 Checking emoji font support..."

ask_consent() {
    local prompt="$1"
    if [ -t 0 ]; then
        read -r -p "$prompt [Y/n] " response
        case "$response" in
            [nN][oO]|[nN])
                return 1
                ;;
            *)
                return 0
                ;;
        esac
    else
        echo "$prompt [Auto-accepting in non-interactive mode]"
        return 0
    fi
}

# 1. Check if fonts-noto-color-emoji is installed
NOTO_INSTALLED=false
if fc-list : family 2>/dev/null | grep -qi "Noto Color Emoji"; then
    NOTO_INSTALLED=true
elif dpkg -s fonts-noto-color-emoji 2>/dev/null | grep -q "Status: install ok installed"; then
    NOTO_INSTALLED=true
fi

if [ "$NOTO_INSTALLED" = false ]; then
    echo "ℹ️  'fonts-noto-color-emoji' is not installed."
    echo "   Without it, terminal emojis may render as missing glyphs or flat monochrome wireframes."
    if ask_consent "Would you like to install fonts-noto-color-emoji?"; then
        echo "Installing fonts-noto-color-emoji..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y fonts-noto-color-emoji || true
        elif command -v apt &>/dev/null; then
            sudo apt update && sudo apt install -y fonts-noto-color-emoji || true
        fi
        fc-cache -f 2>/dev/null || true
    else
        echo "Skipping installation of fonts-noto-color-emoji."
    fi
else
    echo "✅ 'Noto Color Emoji' font is installed."
fi

# 2. Check if Noto Color Emoji is prioritized over monochrome/symbol fonts
if command -v fc-match &>/dev/null; then
    system_mono=$(fc-match monospace 2>/dev/null | cut -d: -f2 | tr -d ' "' | head -n 1)
    test_font="${system_mono:-monospace}"
    top_emoji_font=$(fc-match -s "$test_font:charset=1f4c4" 2>/dev/null | head -n 1)
    if [[ "$top_emoji_font" != *"NotoColorEmoji"* && "$top_emoji_font" != *"Noto Color Emoji"* ]]; then
        echo ""
        echo "⚠️  Monochrome/symbol font takes priority over Noto Color Emoji in terminal fonts:"
        echo "   Target font: $test_font"
        echo "   Current primary fallback: $top_emoji_font"
        echo "   (This causes icons to display as flat 2D wireframes instead of vibrant full-color 3D emojis)"
        if ask_consent "Would you like to prioritize Noto Color Emoji for vibrant 3D icons?"; then
            USER_FONTCONFIG_DIR="$HOME/.config/fontconfig/conf.d"
            mkdir -p "$USER_FONTCONFIG_DIR"
            EMOJI_CONF="$USER_FONTCONFIG_DIR/99-noto-color-emoji.conf"
            cat << 'EOF' > "$EMOJI_CONF"
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <!-- Prioritize Noto Color Emoji over monochrome/symbol fonts for all terminal fonts & emoji -->
  <match target="pattern">
    <edit name="family" mode="append" binding="strong">
      <string>Noto Color Emoji</string>
    </edit>
  </match>
  <alias>
    <family>emoji</family>
    <prefer>
      <family>Noto Color Emoji</family>
    </prefer>
  </alias>
</fontconfig>
EOF
            fc-cache -fv "$USER_FONTCONFIG_DIR" 2>/dev/null || fc-cache -fv 2>/dev/null || true
            echo "✅ Successfully prioritized Noto Color Emoji in $EMOJI_CONF"
            # If a background terminal daemon is running (like deepin-terminal), advise restarting it
            if pgrep -x "deepin-terminal" &>/dev/null; then
                echo "   💡 Note: deepin-terminal runs as a background process. Run 'killall deepin-terminal' to reload fonts."
            fi
        else
            echo "Skipping emoji font prioritization."
        fi
    else
        echo "✅ 'Noto Color Emoji' is already prioritized for terminal emojis ($test_font)."
    fi
fi



# Determine install target directory
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$REPO_DIR/ez"

INSTALL_DIR="/usr/local/bin"
if [ -w "$INSTALL_DIR" ]; then
    ln -sf "$REPO_DIR/ez" "$INSTALL_DIR/ez"
    rm -f "$INSTALL_DIR/ezcli" 2>/dev/null || true
    echo "✅ Successfully linked ez to $INSTALL_DIR/ez"
else
    echo "Creating symlink in $INSTALL_DIR (requires sudo)..."
    sudo ln -sf "$REPO_DIR/ez" "$INSTALL_DIR/ez"
    sudo rm -f "$INSTALL_DIR/ezcli" 2>/dev/null || true
    echo "✅ Successfully installed ez to $INSTALL_DIR/ez"
fi

echo ""
echo "🎉 Installation complete! You can now run 'ez' from anywhere."
echo "Try running:"
echo "    ez"
echo "    ez system-info"
