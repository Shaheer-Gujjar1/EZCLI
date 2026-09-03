# EasyCLI (`ezcli`) v0.2

**EasyCLI** is a beginner-friendly terminal frontend wrapper for Linux commands built specifically for Debian-based systems. It simplifies complex and verbose Linux tasks into beautiful, color-coded terminal cards, interactive menus, a modern graphical file explorer, and safety-first file operations with undo.

---

## 🎯 Target Platforms

EasyCLI is tailored for Debian-based distributions:
- **Linux Mint**
- **Ubuntu**
- **Debian**
- **Zorin OS**
- **Deepin**
- **UbuntuDDE**
- Pop!_OS, Elementary OS, and other Debian/Ubuntu derivatives.

Distributions are automatically detected via `/etc/os-release` and verified for standard Debian utilities (`apt`, `dpkg`, and `systemd`).

---

## 🛡️ Safety & Reliability Philosophy

- **System Inspection Commands:** 100% read-only. Never modifies services, network, packages, or files. Never requires root privileges or invokes `sudo`.
- **File Operations (`copy`, `move`):** Always preview before write. Never silently overwrites existing files. Offers conflict policies (`ask`, `skip`, `overwrite`, `rename`). Cross-filesystem moves verify file sizes and SHA256 checksums before removing source items.
- **Reversible Undo (`ezcli undo`):** Reverts the most recent copy or move. For copies, deletes only newly created destination files (pre-existing files are never touched).
- **Graceful Fault Tolerance:** Missing tools, empty outputs, or permission limits are handled with friendly diagnostic panels rather than crashes or Python tracebacks.

---

## 🚀 Installation & Quick Start

### Prerequisites
- Python 3.8+ (Python 3.12+ tested)
- `python3-rich` (`sudo apt install python3-rich` or `pip install rich`)
- An emoji font (`sudo apt install fonts-noto-color-emoji`)

### Quick Install (Automated)
Run the automated installer to link `ezcli` globally to `/usr/local/bin`:
```bash
./install.sh
```

### Running Directly (No Installation Needed)
```bash
# Make the script runnable
chmod +x ezcli

# Run the interactive menu
./ezcli

# Or run a subcommand directly
./ezcli system-info
```

### Installing via pip
```bash
pip install -e .
# Now ezcli is available anywhere in your PATH
ezcli help
```

---

## 💻 Testing on Another PC

To test EasyCLI on another Debian or Ubuntu machine:

### Option 1: Via Git / GitHub (Recommended)
1. Push your changes to your Git repository:
   ```bash
   git add .
   git commit -m "feat: EasyCLI v0.1 release"
   git push
   ```
2. On your other PC, clone and install:
   ```bash
   git clone <your-repo-url>
   cd EZCLI
   ./install.sh
   ezcli
   ```

### Option 2: Copying via Network (`scp`)
Transfer the folder directly to your other PC:
```bash
# From this PC:
scp -r /home/shaheer/Documents/GitHub/EZCLI user@<other-pc-ip>:~/EZCLI

# On the other PC:
cd ~/EZCLI
./install.sh
ezcli
```

### Option 3: Copying via USB Drive / Archive
Create a compressed archive to move via USB or cloud drive:
```bash
tar -czvf ezcli-v0.1.tar.gz -C /home/shaheer/Documents/GitHub EZCLI

# On the other PC, extract and run:
tar -xzvf ezcli-v0.1.tar.gz
cd EZCLI
./install.sh
ezcli
```

---

## 🖥️ Hybrid User Experience

EasyCLI offers two distinct ways to interact:

1. **Interactive TUI Menu (`ezcli`)**: Running `ezcli` without arguments opens an interactive terminal menu listing all features with inline emoji icons, descriptions, and action controls (`[b]` Back, `[r]` Refresh, `[q]` Quit).
2. **Direct CLI Commands (`ezcli <subcommand> [args]`)**: Running `ezcli` with a subcommand directly prints formatted output to stdout, ideal for experienced users, quick checks, and scripting.

To view all commands and syntax:
```bash
ezcli help
```

---

## 📋 Available Subcommands

| Icon | Subcommand & Syntax | Wrapped Tools | Description |
| :---: | :--- | :--- | :--- |
| 💻 | `ezcli system-info` | `hostnamectl`, `uptime -p`, `/etc/os-release` | Key-value card with OS name/version, hostname, kernel, architecture, and uptime. |
| ⚡ | `ezcli stats` | `free -h`, `uptime`, `nproc` | CPU load averages and RAM/Swap usage with colored inline progress bars. |
| 💽 | `ezcli disk-info` | `df -h` | Table of storage mounts, sizes, used/available space, and inline usage bars (filters out pseudo-filesystems). |
| 📁 | `ezcli big-files [folder]` | `du -h --max-depth=1`, `find` | Table of largest files and folders in directory with a progress spinner. Defaults to `~`. |
| 🔍 | `ezcli package-search <term>` | `apt search`, `flathub`, `snapcraft` | Universal search across **APT 📦**, **Flatpak 🟣**, and **Snap 🟢** with interactive platform selection & installation commands. |
| 📦 | `ezcli package <name>` | `apt show`, `dpkg -s` | Card showing package version, size, homepage, description, and installed status. |
| 🔄 | `ezcli available-updates` | `apt list --upgradable` | Table of upgradable packages and versions using existing lists only (never runs `apt update`). |
| ⚙️ | `ezcli service-status <name>` | `systemctl is-active`, `systemctl is-enabled` | Status card with running state and boot enablement indicators. |
| 🌐 | `ezcli network-info` | `ip addr`, `ip route`, `/etc/resolv.conf` | Overview card and table of network interfaces, IP addresses, gateway, DNS, and online status. |
| 📄 | `ezcli logs [N]` | `journalctl -n N --no-pager` | Color-coded system logs by severity (errors red, warnings yellow, ok green). Defaults to 50 lines. |
| 📋 | `ezcli installed-packages` | `apt list --installed`, `dpkg-query`, `flatpak list`, `snap list` | List all installed packages across system and desktop platforms (wraps `apt list --installed`). |
| 🔎 | `ezcli installed-package-search <name>` | `apt list --installed \| grep -i <name>`, `dpkg-query` | Search installed packages and applications by name (wraps `apt list --installed \| grep -i <name>`). |
| 📁 | `ezcli choose-directory [path]` | `explorer` | Graphical terminal file explorer with mouse navigation, file-type emojis, bookmarks, and subshell launcher. |
| 📋 | `ezcli copy` | `cp` | Choose file(s) or folder(s) to copy using the mini file explorer and stage to clipboard. |
| 🚚 | `ezcli move` | `mv` | Choose file(s) or folder(s) to move using the mini file explorer and stage to clipboard. |
| 📥 | `ezcli paste` | `paste` | Choose destination folder using the mini explorer, preview summary, confirm with y/n, and paste. |
| ⏪ | `ezcli undo` | `undo` | Revert the most recent paste operation with preview and confirmation. |
| ⏩ | `ezcli redo` | `redo` | Re-apply the most recently undone operation with preview and confirmation. |

---

## 📁 Terminal File Explorer (`choose-directory`)

EasyCLI includes a visual terminal file manager designed for beginners:
```bash
ezcli choose-directory
```

### Controls & Features
- **Mouse Navigation**: Click any item to select/highlight; double-click a folder to enter.
- **`[Enter]`**: Open/enter directory.
- **`[Space]`**: Multi-select items.
- **`[/]`**: Instant search-as-you-type filter.
- **`[p]`**: Quick Places menu (`🏠 Home`, `📥 Downloads`, `📄 Documents`, `🖥️ Desktop`, `🕒 Recent`, `⭐ Bookmarks`).
- **`[h]`**: Toggle hidden files (dotfiles).
- **`[s]`**: Cycle sort order (`Name`, `Size`, `Date`).
- **`[i]`**: Toggle item info sidebar (file size, permissions, owner, timestamps).
- **`[b]`**: Bookmark the current directory.
- **`[c]`**: Confirm chosen directory and open the Action Menu.
- **`[q]`**: Quit explorer.

### "Open Shell Here" & Parent Shells
When you confirm a directory and choose **"Open shell here"**, EasyCLI spawns your default shell (`$SHELL`) directly in that directory. 
> **Note**: In Linux, child processes cannot change the directory of their parent terminal shell. Running an embedded subshell allows you to work directly in the target directory. Type `exit` (or press `Ctrl+D`) at any time to return to your previous shell session.

### Direct `cd` Shell Integration (`ezcd`)
If you would like a command that directly `cd`s your current shell into the chosen directory without launching a subshell, add this 3-line function to your `~/.bashrc` (or `~/.zshrc`):
```bash
ezcd() {
    local target
    target=$(ezcli choose-directory -p "$@")
    [ -d "$target" ] && cd "$target"
}
```
Reload with `source ~/.bashrc`. Now running `ezcd` opens the visual file manager, and pressing `c` immediately changes your shell's working directory!

---

## 📋 Visual Copy, Move, Paste, Undo & Redo

EasyCLI v0.2 makes terminal file operations as simple as a graphical file manager:

### 1. Copy Files or Folders
```bash
ezcli copy
```
- Launches the mini file explorer in multi-select mode.
- Highlight items, press `[Space]` to select, then press `[c]` or `[Enter]` to confirm.
- Selected items are staged onto your EasyCLI clipboard with a confirmation card.

### 2. Move / Cut Files or Folders
```bash
ezcli move
```
- Launches the mini file explorer to select files/folders to move.
- Selected items are staged for moving.

### 3. Paste to Destination
```bash
ezcli paste
```
- Launches the mini explorer to choose your destination directory.
- After selecting, displays a **Beautiful Summary Card** showing total items, combined size, destination, and any existing file conflicts.
- Prompts for conflict policy if items exist (`ask`, `skip`, `overwrite`, `rename`).
- Asks for `[y/N]` confirmation before touching any files.
- Executes with a live per-file progress bar.

### 4. Undo (`ezcli undo`)
To safely revert your most recent paste operation:
```bash
ezcli undo
```
- Displays an undo preview card and asks for `[y/N]` confirmation.
- **Moves**: Files are moved back to their original source paths.
- **Copies**: Only files newly created at destination are removed; pre-existing files are never touched.

### 5. Redo (`ezcli redo`)
If you change your mind and want to re-apply an undone operation:
```bash
ezcli redo
```
- Displays a redo preview card and asks for `[y/N]` confirmation.
- Re-applies the operation and updates the undo history.


## 🎨 Icon & Font Policy

- **Emoji Icons:** Single-character inline emoji icons are used throughout the application without adding extra lines or disrupting grid alignment.
- **Structural Layouts:** All borders, panels, tables, and usage bars use standard ASCII/box-drawing characters (`╭─╮`, `│`, `╰─╯`, `█`, `░`).
- **Capability Detection:** On startup, EasyCLI detects whether your terminal and system support emoji fonts (via fontconfig / font inspection). If the emoji font is missing, it offers to install `fonts-noto-color-emoji` via apt or exits with a clear setup guide. It never degrades to inconsistent ASCII icons.

---

## 🏗️ Code Architecture

EasyCLI is designed with a layered, decoupled architecture:

```
EZCLI/
├── ezcli                  # Executable entrypoint script
├── pyproject.toml         # Packaging configuration (v0.2.0)
├── setup.py               # Setup script
├── install.sh             # 1-step deployment script
├── README.md              # Documentation and guide
├── tests/                 # Comprehensive unit test suite (35 tests)
│   ├── test_distro.py     # Distro parser and derivative detection tests
│   ├── test_collectors.py # System inspection and installed package tests
│   ├── test_file_ops.py   # Copy, move, cross-filesystem, and conflict tests
│   ├── test_undo.py       # Reversible undo engine verification
│   └── test_cli.py        # CLI dispatch, flags, and end-to-end flow tests
└── ezcli_app/
    ├── __init__.py        # Package version (__version__ = "0.2.0")
    ├── config.py          # Declarative FeatureTemplate definitions & aliases
    ├── distro.py          # /etc/os-release parsing and Debian validation
    ├── emoji.py           # Font capability and UTF-8 detection
    ├── collectors.py      # Subprocess execution and multi-platform queries
    ├── renderers.py       # Rich visual layout and box-drawing renderers
    ├── menu.py            # Interactive TUI menu and keyboard navigation
    ├── main.py            # Subcommand parser and dispatcher
    ├── file_engine.py     # Safe file operations, SHA256 checks, conflict policies
    ├── file_cli.py        # Interactive copy, move, and undo CLI handlers
    ├── undo.py            # Reversible undo history engine (~/.local/share/ezcli)
    └── explorer/          # Textual TUI File Explorer
        ├── file_icons.py  # Emoji mapping per file extension and MIME type
        ├── places.py      # Bookmarks and standard quick places
        └── explorer_app.py# Reusable file manager and directory picker
```

---

## 🧪 Running Tests

To run the automated unit test suite:
```bash
python3 -m unittest discover tests/
```

All 35 unit tests validate distro detection, collector safety, file operations, conflict policies, cross-filesystem moves, undo engine, command parsing, and CLI flags.
