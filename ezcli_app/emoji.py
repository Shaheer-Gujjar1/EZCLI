"""Emoji font capability detection and first-run setup."""

import glob
import os
import shutil
import subprocess
import sys
from typing import Tuple


def has_emoji_font() -> bool:
    """Detect if an emoji font is installed on the system."""
    # 1. Check via fontconfig fc-list if available
    fc_list_path = shutil.which("fc-list")
    if fc_list_path:
        try:
            res = subprocess.run(
                [fc_list_path, ":", "family"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                output = res.stdout.lower()
                if "emoji" in output or "twemoji" in output:
                    return True
        except Exception:
            pass

    # 2. Check font paths on filesystem directly
    font_patterns = [
        "/usr/share/fonts/**/*emoji*",
        "/usr/share/fonts/**/*Emoji*",
        "/usr/local/share/fonts/**/*emoji*",
        "~/.local/share/fonts/**/*emoji*",
        "~/.fonts/**/*emoji*",
    ]
    for pattern in font_patterns:
        expanded = os.path.expanduser(pattern)
        matches = glob.glob(expanded, recursive=True)
        if matches:
            return True

    # 3. Check fc-match if available
    fc_match_path = shutil.which("fc-match")
    if fc_match_path:
        try:
            res = subprocess.run(
                [fc_match_path, "emoji"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and "emoji" in res.stdout.lower():
                return True
        except Exception:
            pass

    return False


def can_render_unicode() -> bool:
    """Check if stdout encoding supports UTF-8 Unicode characters."""
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "💻⚡💽📁🔍📦🔄⚙️🌐📄".encode(encoding)
        return True
    except UnicodeEncodeError:
        return False


def ensure_emoji_capability(interactive: bool = True) -> bool:
    """
    Ensure emoji font and rendering capability are available.
    If missing, prompts to install fonts-noto-color-emoji via apt.
    If user declines or emoji cannot render, prints a setup message and exits gracefully.
    Never falls back to ASCII icons.
    """
    if not can_render_unicode():
        print(
            "\n[EasyCLI Setup] Error: Your terminal does not support UTF-8 character encoding.\n"
            "EasyCLI requires a UTF-8 capable terminal to render its interface and icons.\n"
            "Please configure your terminal locale to UTF-8 (e.g. export LANG=en_US.UTF-8) and retry.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    if has_emoji_font():
        return True

    # Emoji font is missing
    print("\n" + "=" * 65)
    print(" [EasyCLI Setup] Emoji Font Required")
    print("=" * 65)
    print(
        "EasyCLI uses single-character emoji icons for a clean, intuitive TUI.\n"
        "No emoji font was detected on your system (e.g. fonts-noto-color-emoji).\n"
    )

    if not interactive or not sys.stdin.isatty():
        print(
            "To install the recommended emoji font, run:\n"
            "    sudo apt install -y fonts-noto-color-emoji\n\n"
            "Then restart your terminal and launch ez again.\n"
        )
        sys.exit(1)

    try:
        reply = input("Would you like to install fonts-noto-color-emoji now via apt? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)

    if reply in ("y", "yes"):
        print("\nRunning: sudo apt install -y fonts-noto-color-emoji ...\n")
        try:
            ret = subprocess.run(["sudo", "apt", "install", "-y", "fonts-noto-color-emoji"])
            if ret.returncode == 0:
                print(
                    "\n✅ Emoji font installed successfully!\n"
                    "Please restart your terminal to reload the font cache, then run 'ez'.\n"
                )
                sys.exit(0)
            else:
                print("\nInstallation failed. You may run: sudo apt install fonts-noto-color-emoji manually.")
                sys.exit(1)
        except Exception as e:
            print(f"\nCould not run installer: {e}")
            sys.exit(1)
    else:
        print(
            "\nEasyCLI requires an emoji font to display properly.\n"
            "You can install it manually at any time with:\n"
            "    sudo apt install fonts-noto-color-emoji\n\n"
            "Then restart your terminal and run ez.\n"
        )
        sys.exit(1)
