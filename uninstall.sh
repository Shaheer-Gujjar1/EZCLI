#!/usr/bin/env bash
set -e

echo "=== EasyCLI (ez) Uninstaller ==="

ask_consent() {
    local prompt="$1"
    local default="${2:-Y}"
    if [ -t 0 ]; then
        if [ "$default" = "Y" ]; then
            read -r -p "$prompt [Y/n] " response
            case "$response" in
                [nN][oO]|[nN]) return 1 ;;
                *) return 0 ;;
            esac
        else
            read -r -p "$prompt [y/N] " response
            case "$response" in
                [yY][eE][sS]|[yY]) return 0 ;;
                *) return 1 ;;
            esac
        fi
    else
        echo "$prompt [Auto-proceeding in non-interactive mode]"
        return 0
    fi
}

# 1. Remove binary symlinks (/usr/local/bin/ez and /usr/local/bin/ezcli)
INSTALL_DIR="/usr/local/bin"
removed_symlink=false
for bin in "$INSTALL_DIR/ez" "$INSTALL_DIR/ezcli"; do
    if [ -L "$bin" ] || [ -f "$bin" ]; then
        echo "Removing $bin..."
        if [ -w "$INSTALL_DIR" ]; then
            rm -f "$bin"
        else
            sudo rm -f "$bin"
        fi
        removed_symlink=true
    fi
done

if [ "$removed_symlink" = true ]; then
    echo "✅ Removed command symlink(s) from $INSTALL_DIR."
else
    echo "ℹ️  No symlinks found in $INSTALL_DIR."
fi

# 2. Remove user data directories (~/.local/share/ez and ~/.local/share/ezcli)
DATA_DIRS=("$HOME/.local/share/ez" "$HOME/.local/share/ezcli")
found_data=false
for dir in "${DATA_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        found_data=true
    fi
done

if [ "$found_data" = true ]; then
    echo ""
    if ask_consent "Remove EasyCLI user data, bookmarks, undo history, and local virtualenv (~/.local/share/ez)?"; then
        for dir in "${DATA_DIRS[@]}"; do
            if [ -d "$dir" ]; then
                rm -rf "$dir"
                echo "✅ Removed $dir"
            fi
        done
    else
        echo "Preserved user data in ~/.local/share/ez."
    fi
fi

# 3. Optional: Fontconfig override
EMOJI_CONF="$HOME/.config/fontconfig/conf.d/99-noto-color-emoji.conf"
if [ -f "$EMOJI_CONF" ]; then
    echo ""
    if ask_consent "Remove Noto Color Emoji font prioritization ($EMOJI_CONF)?" "N"; then
        rm -f "$EMOJI_CONF"
        fc-cache -fv "$HOME/.config/fontconfig/conf.d" 2>/dev/null || fc-cache -fv 2>/dev/null || true
        echo "✅ Removed font configuration override."
    else
        echo "Preserved Noto Color Emoji font configuration."
    fi
fi

echo ""
echo "🎉 EasyCLI has been successfully uninstalled."
echo "   (You can now safely delete the repository folder if desired)."
