# EasyCLI (`ez`) v0.3

**EasyCLI** is a beginner-friendly terminal frontend wrapper for Linux commands built specifically for Debian-based systems. It simplifies complex and verbose Linux tasks into beautiful, color-coded terminal cards, interactive menus, a modern graphical file explorer, safety-first file operations with reversible undo, modern file creation/deletion, and seamless automatic privilege elevation.

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

- **System Inspection Commands (v0.1):** 100% read-only. Never modifies services, network, packages, or files. Never requires root privileges or invokes `sudo`.
- **File Operations (v0.2 - `copy`, `move`):** Always preview before write. Never silently overwrites existing files. Offers conflict policies (`ask`, `skip`, `overwrite`, `rename`). Cross-filesystem moves verify file sizes and SHA256 checksums before removing source items.
- **Reversible Undo (v0.2 - `ez undo`):** Reverts the most recent copy or move. For copies, deletes only newly created destination files (pre-existing files are never touched).
- **Creation & Deletion Commands (v0.3 - `create-folder`, `create-file`, `delete`):** Replaces legacy `mkdir`, `touch`, and `rm`. Direct commands are strictly scoped to the current directory to prevent accidents. `delete` always runs without force first and demands explicit consent before touching any files.
- **Shared Privilege Elevation (v0.3):** 100% automatic elevation without `--admin` flags. Never runs the application under sudo (`sudo ez`). Only specific privileged tasks are elevated through a lightweight helper with dot password feedback (`••••`).
- **Graceful Fault Tolerance:** Missing tools, empty outputs, or permission limits are handled with friendly diagnostic panels rather than crashes or Python tracebacks.

---

## 🚀 Installation & Quick Start

### Prerequisites
- Python 3.8+ (Python 3.12+ tested)
- `python3-rich` (`sudo apt install python3-rich` or `pip install rich`)
- An emoji font (`sudo apt install fonts-noto-color-emoji`)

### Quick Install (Automated)
Run the automated installer to link `ez` globally to `/usr/local/bin`:
```bash
./install.sh
```

### Running Directly (No Installation Needed)
```bash
# Make the script runnable
chmod +x ez

# Run the interactive menu
./ez

# Or run a subcommand directly
./ez system-info
```

### Installing via pip
```bash
pip install -e .
# Now ez is available anywhere in your PATH
ez help
```

---

## 💻 Testing on Another PC

To test EasyCLI on another Debian or Ubuntu machine:

### Option 1: Via Git / GitHub (Recommended)
1. Push your changes to your Git repository:
   ```bash
   git add .
   git commit -m "feat: EasyCLI v0.3 release"
   git push
   ```
2. On your other PC, clone and install:
   ```bash
   git clone <your-repo-url>
   cd EZCLI
   ./install.sh
   ez
   ```

### Option 2: Copying via Network (`scp`)
Transfer the folder directly to your other PC:
```bash
# From this PC:
scp -r /home/shaheer/Documents/GitHub/EZCLI user@<other-pc-ip>:~/EZCLI

# On the other PC:
cd ~/EZCLI
./install.sh
ez
```

### Option 3: Copying via USB Drive / Archive
Create a compressed archive to move via USB or cloud drive:
```bash
tar -czvf ez-v0.3.tar.gz -C /home/shaheer/Documents/GitHub EZCLI

# On the other PC, extract and run:
tar -xzvf ez-v0.3.tar.gz
cd EZCLI
./install.sh
ez
```

---

## 🖥️ Hybrid User Experience

EasyCLI offers two distinct ways to interact:

1. **Interactive TUI Menu (`ez`)**: Running `ez` without arguments opens an interactive terminal menu listing all features with inline emoji icons, descriptions, and action controls (`[b]` Back, `[r]` Refresh, `[q]` Quit).
2. **Direct CLI Commands (`ez <subcommand> [args]`)**: Running `ez` with a subcommand directly prints formatted output to stdout, ideal for experienced users, quick checks, and scripting.

To view all commands and syntax:
```bash
ez help
```

---

## 📋 Available Subcommands

| Icon | Subcommand & Syntax | Version | Wrapped Tools | Description |
| :---: | :--- | :---: | :--- | :--- |
| 💻 | `ez system-info` | **v0.1** | `hostnamectl`, `uptime -p`, `/etc/os-release` | Key-value card with OS name/version, hostname, kernel, architecture, and uptime. |
| ⚡ | `ez stats` | **v0.1** | `free -h`, `uptime`, `nproc` | CPU load averages and RAM/Swap usage with colored inline progress bars. |
| 💽 | `ez disk-info` | **v0.1** | `df -h` | Table of storage mounts, sizes, used/available space, and inline usage bars (filters out pseudo-filesystems). |
| 📁 | `ez big-files [path \| choose-directory]` | **v0.1** | `du -h --max-depth=1`, `find` | Table of largest files and folders. Provide a path or use `choose-directory` to pick visually via the mini explorer. Defaults to `~`. |
| 🔍 | `ez package-search <term>` | **v0.1** | `apt search`, `flathub`, `snapcraft` | Universal search across **APT 📦**, **Flatpak 🟣**, and **Snap 🟢** with interactive platform selection & installation commands. |
| 📦 | `ez package <name>` | **v0.1** | `apt show`, `dpkg -s` | Card showing package version, size, homepage, description, and installed status. |
| 🔄 | `ez available-updates` | **v0.1** | `apt list --upgradable` | Table of upgradable packages and versions using existing lists only (never runs `apt update`). |
| ⚙️ | `ez service-status <name>` | **v0.1** | `systemctl is-active`, `systemctl is-enabled` | Status card with running state and boot enablement indicators. |
| 🌐 | `ez network-info` | **v0.1** | `ip addr`, `ip route`, `/etc/resolv.conf` | Overview card and table of network interfaces, IP addresses, gateway, DNS, and online status. |
| 📄 | `ez logs [N]` | **v0.1** | `journalctl -n N --no-pager` | Color-coded system logs by severity (errors red, warnings yellow, ok green). Defaults to 50 lines. |
| 📋 | `ez installed-packages` | **v0.1** | `apt list --installed`, `dpkg-query`, `flatpak list`, `snap list` | List all installed packages across system and desktop platforms (wraps `apt list --installed`). |
| 🔎 | `ez installed-package-search <name>` | **v0.1** | `apt list --installed \| grep -i <name>`, `dpkg-query` | Search installed packages and applications by name (wraps `apt list --installed \| grep -i <name>`). |
| 📁 | `ez choose-directory [path]` | **v0.2** | `explorer` | Graphical terminal file explorer with mouse navigation, file-type emojis, bookmarks, and subshell launcher. |
| 📋 | `ez copy [target \| choose-directory]` | **v0.2** | `cp` | Copy file/folder in current directory directly or choose visually with `choose-directory`. |
| 🚚 | `ez move [target \| choose-directory]` | **v0.2** | `mv` | Move file/folder in current directory directly or choose visually with `choose-directory`. |
| 📥 | `ez paste [choose-directory]` | **v0.2** | `paste` | Paste staged items into current directory, or choose destination with `choose-directory`. |
| ⏪ | `ez undo` | **v0.2** | `undo` | Revert the most recent paste operation with preview and confirmation. |
| ⏩ | `ez redo` | **v0.2** | `redo` | Re-apply the most recently undone operation with preview and confirmation. |
| 📁 | `ez create-folder <name> [choose-directory]` | **v0.3** | `create-folder` | Create a new folder directly or choose parent directory visually with mini explorer. Automatic privilege elevation. |
| 📄 | `ez create-file <name> [choose-directory]` | **v0.3** | `create-file` | Create a new blank file directly or choose destination directory visually with mini explorer. Automatic privilege elevation. |
| 🗑️ | `ez delete [target \| choose-directory]` | **v0.3** | `delete` | Permanently delete file(s) or folder(s) with explicit consent, non-force-first safety, and automatic elevation. |
| 📝 | `ez edit-file [target \| choose-directory]` | **v0.3** | `edit-file` | Modern terminal text and code editor with syntax highlighting, line numbers, visual search, and auto-elevation. |

---

## 📁 Terminal File Explorer (`choose-directory`)

EasyCLI includes a visual terminal file manager designed for beginners:
```bash
ez choose-directory
```

### Controls & Features
- **Mouse Navigation**: Click any item to select/highlight; double-click a folder to enter.
- **`[Enter]`**: Open/enter directory.
- **`[Space]`**: Multi-select items.
- **`[n]`**: Create a new folder or blank file directly in the current directory.
- **`[/]`**: Instant search-as-you-type filter.
- **`[p]`**: Quick Places menu (`🏠 Home`, `📥 Downloads`, `📄 Documents`, `🖥️ Desktop`, `🕒 Recent`, `⭐ Bookmarks`).
- **`[h]`**: Toggle hidden files (dotfiles).
- **`[s]`**: Cycle sort order (`Name`, `Size`, `Date`).
- **`[i]`**: Toggle item info sidebar (file size, permissions, owner, timestamps).
- **`[b]`**: Bookmark the current directory.
- **`[c]`**: Confirm chosen directory and open the Action Menu (`Open shell here`, `Copy path to clipboard`, `Directory information`).
- **`[q]`**: Quit explorer.

### "Open Shell Here" & Parent Shells
When you confirm a directory and choose **"Open shell here"**, EasyCLI spawns your default shell (`$SHELL`) directly in that directory. 
> **Note**: In Linux, child processes cannot change the directory of their parent terminal shell. Running an embedded subshell allows you to work directly in the target directory. Type `exit` (or press `Ctrl+D`) at any time to return to your previous shell session.

### Direct `cd` Shell Integration (`ezcd`)
If you would like a command that directly `cd`s your current shell into the chosen directory without launching a subshell, add this 3-line function to your `~/.bashrc` (or `~/.zshrc`):
```bash
ezcd() {
    local target
    target=$(ez choose-directory -p "$@")
    [ -d "$target" ] && cd "$target"
}
```
Reload with `source ~/.bashrc`. Now running `ezcd` opens the visual file manager, and pressing `c` immediately changes your shell's working directory!

---

## 📋 Safe Copy, Move, Paste, Undo & Redo (v0.2)

EasyCLI provides modern, visual, and direct file operations with reversible undo:

### 1. Copy Files or Folders (`ez copy`)
- **Direct file in current directory:**
  ```bash
  ez copy notes.txt
  ```
- **Direct folder in current directory:**
  ```bash
  ez copy my_project/
  ```
  *(Direct copy is strictly scoped to the current directory. Subfolder paths like `sub/file.txt` are safely rejected with advice to use `choose-directory`)*
- **Choose file(s) or folder(s) visually anywhere:**
  ```bash
  ez copy choose-directory
  # Or simply:
  ez copy
  ```
  Launches the mini file explorer in multi-select mode. Highlight items, press `[Space]` to select, then press `[c]` or `[Enter]` to confirm. Selected items are staged onto your EasyCLI clipboard with an immediate summary card.

### 2. Move / Cut Files or Folders (`ez move`)
- **Direct file in current directory:**
  ```bash
  ez move notes.txt
  ```
- **Direct folder in current directory:**
  ```bash
  ez move my_project/
  ```
- **Choose file(s) or folder(s) visually anywhere:**
  ```bash
  ez move choose-directory
  # Or simply:
  ez move
  ```

### 3. Paste to Destination (`ez paste`)
- **Paste into current directory:**
  ```bash
  ez paste
  ```
  Pastes staged items directly into your current working directory without launching the mini explorer!
- **Choose destination folder visually anywhere:**
  ```bash
  ez paste choose-directory
  ```
  Launches the mini explorer to navigate and choose your destination directory.
- **Safety & Preview:**
  - Displays a **Beautiful Summary Card** showing total items, combined size, destination, and any existing file conflicts.
  - Prompts for conflict policy if items exist (`ask`, `skip`, `overwrite`, `rename`).
  - Asks for `[y/N]` confirmation before touching any files.
  - Executes with a live per-file progress bar.

### 4. Undo (`ez undo`)
To safely revert your most recent paste operation:
```bash
ez undo
```
- Displays an undo preview card and asks for `[y/N]` confirmation.
- **Moves**: Files are moved back to their original source paths.
- **Copies**: Only files newly created at destination are removed; pre-existing files are never touched.

### 5. Redo (`ez redo`)
If you change your mind and want to re-apply an undone operation:
```bash
ez redo
```
- Displays a redo preview card and asks for `[y/N]` confirmation.
- Re-applies the operation and updates the undo history.

---

## ✨ Creating Files & Folders (v0.3: `create-folder`, `create-file`)

EasyCLI v0.3 introduces pure, modern creation commands without needing to memorize legacy commands:

### 1. Create a Folder Directly
```bash
ez create-folder my_project
```
Creates a new directory in your current location with an immediate summary card.

### 2. Choose Where to Create Visually
```bash
ez create-folder my_project choose-directory
# Or simply:
ez create-folder choose-directory
```
Opens the mini file explorer so you can navigate and pick your desired parent directory visually.

### 3. Create Blank Files
```bash
ez create-file notes.txt
# Or choose directory visually:
ez create-file notes.txt choose-directory
```

### 4. Create Directly Inside the File Explorer (`[n]`)
While browsing files with `ez choose-directory`:
- Press **`[n]`** at any time to create a new folder or file.
- Choose between **Folder 📁** or **Blank File 📄**.
- Enter your item name and press `[Enter]`.
- If the current folder is protected (such as `/etc`), EasyCLI prompts for admin authorization automatically.
- The directory view instantly refreshes with your newly created item.

---

## 🗑️ Safe File & Folder Deletion (v0.3: `delete`)

EasyCLI v0.3 replaces dangerous and silent `rm` / `rm -rf` commands with a consent-first, error-guarded deletion engine:

### 1. Visual Selection via Mini Explorer
```bash
ez delete choose-directory
# Or simply:
ez delete
```
Opens the mini file explorer in multi-select mode so you can visually choose file(s) and folder(s) anywhere on your system.

### 2. Direct Deletion in Current Directory Only
To prevent accidental destruction of files across unrelated paths, direct deletion is strictly scoped to the **current working directory**:
- **Folder:** `ez delete my_folder/`
- **File:** `ez delete document.pdf`

> **Note:** Specifying subfolder paths (e.g. `folder/sub/` or `sub/file.txt`) directly is intentionally blocked. Use `ez delete choose-directory` to navigate and delete items in other directories safely.

### 3. Always Runs Without Force First
- When deleting folders, EasyCLI attempts standard safe removal first (`rmdir`).
- If a folder is non-empty, EasyCLI will **never** delete it silently. It warns you and explicitly asks:
  ```text
  ⚠️ Folder 'my_project' is not empty and cannot be deleted without force.
  Delete folder and all its contents forcefully? [y/N]
  ```
- If you answer `No` (the default), the folder is safely skipped without any changes.

### 4. Dangerous Commands Require Explicit Consent
Before any files or folders are deleted, EasyCLI displays a full preview card showing item names, types (📄 File vs 📁 Folder), sizes, locations, and total size:
```text
⚠️  DANGER: Permanent Deletion
The following item(s) will be permanently deleted from your system.
This action CANNOT be undone.

Are you sure you want to permanently delete these items? [y/N]
```
The default answer is `No` (`default=False`), ensuring nothing is ever deleted by accident.

### 5. 100% Automatic Elevation (No `--admin` Flag)
If you delete an item in a write-protected location (or encounter a permission error), EasyCLI automatically explains the requirement and prompts for admin authorization (`[Y/n]`).

### 6. Interactive Visual Picker (`choose-directory`)
When you run `ez delete choose-directory` (or simply `ez delete`):
- The mini file explorer opens in dedicated deletion selection mode.
- Navigate to any folder, select one or multiple items using `[Space]` (or highlight an item).
- Press **`[c]`** to confirm your selection for deletion.
- The interactive preview and confirmation prompts appear safely in the terminal before any deletion is executed.

---

## 📝 Mini Text & Code Editor (v0.3: `edit-file`)

EasyCLI v0.3 introduces a beginner-friendly terminal text and code editor to replace cumbersome and unintuitive editors like `nano` and `vi`:

```bash
# Edit a file in current directory
ez edit-file config.py

# Or choose any file visually via the file picker
ez edit-file choose-directory
```

### 1. Direct Editing Scoped to Current Directory
To prevent accidental modifications of files in unintended paths, direct editing is strictly scoped to the **current working directory**:
- **Allowed:** `ez edit-file notes.txt`, `ez edit-file script.py`
- **Protected:** Passing subfolder paths (e.g. `ez edit-file sub/script.py`) is safely rejected with clear instructions to run `ez edit-file choose-directory`.
- **New Files:** If the specified filename does not exist, EasyCLI opens a blank editor buffer and creates the file cleanly upon saving.

### 2. Visual File Picker (`choose-directory`)
When you run `ez edit-file choose-directory` (or `ez edit-file` with no arguments):
- Opens a dedicated file picker for selecting text and code files.
- Navigate directories using arrow keys or mouse; press **`[Enter]`** or **`[c]`** on any file to open it directly in the editor.
- Regular `ez choose-directory` browsing remains 100% clean and isolated.

### 3. Advanced Features & Compact Mouse Controls
- **Compact Bottom Action Bar:** Sleek 1-line action buttons designed to fit even smaller terminal windows without overflowing or wrapping:
  - `[💾 Save]`: Save buffer immediately (auto-prompts elevation if write-protected).
  - `[💾 Save & Exit]`: One-click button to save changes and exit editor immediately.
  - `[🔍 Find]`: Toggles interactive find & replace panel.
  - `[❓ Help]`: Opens mouse-friendly shortcut & controls guide.
  - `[❌ Exit]`: Safely exits editor (prompts to save or discard if unsaved changes exist).
- **Interactive Clickable Status Bar:** Status badges double as instant configuration buttons—click `[📍 Ln, Col]` to jump to line, click `[🔤 Syntax]` to switch language, click `[🎨 Theme]` to change theme, or click `[🔄 Wrap]` to toggle word wrap.
- **Sleek Single-Line Header:** Displays file icon, filename, modification status, admin elevation badge, and path breadcrumb without redundant buttons.
- **Interactive Find & Replace:** Find query, Replace query, Next/Prev navigation, single-match replace, and whole-file Replace All with match counts.
- **Clickable Status Bar:** Status badges are interactive buttons—click line/col to jump to line, click syntax to switch language, click theme to change theme, or click wrap to toggle soft wrap.
- **Line Numbers & Coordinate Status:** Line numbers displayed by default; live cursor coordinates (`Ln 12, Col 5`), line count, file size, encoding, and syntax language indicators.
- **Keyboard Shortcuts:**
  - **`Ctrl + S`**: Save file (prompts for auto-elevation if write-protected).
  - **`Ctrl + X`**: Save and Exit editor immediately (nano-style shortcut).
  - **`Ctrl + Q` / `Esc`**: Exit editor. If you have unsaved changes, displays a safe prompt with `[Save & Exit]`, `[Discard & Exit]`, and `[Cancel]`.
  - **`Ctrl + F`**: Search / Find text in the file with live match counting.
  - **`Ctrl + G` / `Ctrl + L`**: Jump to line number.
  - **`Ctrl + W`**: Toggle soft word wrapping.
  - **`Ctrl + Z` / `Ctrl + Y`**: Undo / Redo edits.
  - **`F2` / `Ctrl + H`**: Open shortcut help cheat sheet.

### 4. Automatic Privilege Elevation with Consent
- If you edit a write-protected system file (such as `/etc/hosts` or system service configurations), EasyCLI will never lose your work or crash with a permission error.
- Upon saving (`Ctrl + S`), EasyCLI explains that admin rights are required and asks for your consent (`[Y/n]`).
- Upon confirmation, EasyCLI saves the file safely via the internal privileged helper without ever requiring you to run `sudo ez`.

### 5. Binary File Protection
EasyCLI detects binary file formats (e.g. `.png`, `.bin`, `.iso`, `.zip`, `.exe`, or files with null bytes) and refuses to open them in text mode, protecting your binary data from accidental corruption.

---

## 🔒 Safe Automatic Privilege Elevation (v0.3)

EasyCLI features a beginner-friendly, secure, and transparent privilege-elevation layer:

### 1. The Core Architecture
- **Never `sudo ez`**: The EasyCLI application always launches and runs as your normal user. You never need to run `sudo ez`, and EasyCLI will never instruct you to do so. Running an entire terminal application under `sudo` can write root-owned config/history files to your home folder and poses security risks.
- **Small Privileged Helper**: Only the specific underlying operation (such as reading system journal files, scanning `/root`, or pasting a file into `/etc`) is elevated through a lightweight internal helper.

### 2. Adaptive Permission Handling
- **Partial Permission Failure**: If some data was successfully collected but some locations were blocked (e.g. `ez big-files` scanning a folder with restricted subfolders, or `ez logs` showing user logs because system journals are restricted), EasyCLI displays all available results first, followed by a friendly offer:
  ```text
  ⚠️ Some locations were inaccessible. Retry with admin rights? [Y/n]
  ```
  On yes, only the blocked portion is elevated and updated.
- **Full Permission Failure**: If the task cannot produce anything without admin rights (e.g. scanning a restricted directory like `/root`), EasyCLI shows a clear explanation card:
  ```text
  🔒 Admin rights are required for this task.
  ```
  and seamlessly offers to run it with admin rights now.
- **Zero Flag Overhead (No `--admin` Needed)**: Users never need to remember or type special admin flags. Everything is handled automatically and transparently via interactive yes/no confirmations.

### 3. Authentication UX
- **Visible Dot Feedback**: During password entry, EasyCLI provides visible bullet feedback (`••••••••`) instead of sudo's silent prompt, making it easy to know your typing is registered.
- **Plain English Explanations**: Before asking for your password, EasyCLI clearly explains what will be done and why admin rights are needed.
- **Friendly Error Messages**: On a mistyped password, EasyCLI displays:
  ```text
  Wrong password — no problem, try again.
  ```
  Never showing raw sudo lectures or warnings.
- **Strict Privacy**: Passwords are never saved or logged; memory buffers are cleared immediately after authentication.

### 4. Risk Guardrails
- **Read-Only Operations (Low Risk)**: Diagnostic scans, log inspection, and status checks require quick yes/no confirmation only.
- **Write Operations (High Risk)**: Pasting, moving, undoing, or redoing into protected system directories displays the full EasyCLI guardrails:
  - **`🛡️ HIGH RISK: System / Protected Location`** badge
  - Impact preview (items, sizes, collisions)
  - Conflict resolution policy (`ask`, `skip`, `overwrite`, `rename`)
  - Explicit confirmation prompt before elevation

### 5. Explorer Integration
In `ez choose-directory`, directories that the normal user cannot read are marked with a lock emoji (`🔒`). Pressing `[Enter]` on a locked folder offers elevation and, on authentication, reloads the directory contents seamlessly.

---

## 🎨 Icon & Font Policy

- **Emoji Icons:** Single-character inline emoji icons are used throughout the application without adding extra lines or disrupting grid alignment.
- **Structural Layouts:** All borders, panels, tables, and usage bars use standard ASCII/box-drawing characters (`╭─╮`, `│`, `╰─╯`, `█`, `░`).
- **Capability Detection:** On startup, EasyCLI detects whether your terminal and system support emoji fonts (via fontconfig / font inspection). If the emoji font is missing, it offers to install `fonts-noto-color-emoji` via apt or exits with a clear setup guide. It never degrades to inconsistent ASCII icons.

---

## 🏗️ Code Architecture

EasyCLI is designed with a layered, decoupled architecture:

```
EZCLI/
├── ez                     # Executable entrypoint script
├── pyproject.toml         # Packaging configuration (v0.3.0)
├── setup.py               # Setup script (v0.3.0)
├── install.sh             # 1-step deployment script
├── README.md              # Documentation and guide
├── tests/                 # Comprehensive unit test suite (103 tests)
│   ├── test_distro.py     # Distro parser and derivative detection tests
│   ├── test_collectors.py # System inspection and installed package tests
│   ├── test_file_ops.py   # Copy, move, cross-filesystem, and conflict tests
│   ├── test_undo.py       # Reversible undo engine verification
│   ├── test_create.py     # File & folder creation validation tests (v0.3)
│   ├── test_delete.py     # Safe deletion, non-force, and consent tests (v0.3)
│   ├── test_editor.py     # Mini text & code editor validation tests (v0.3)
│   ├── test_cli.py        # CLI dispatch, flags, and end-to-end flow tests
│   └── test_elevation.py  # Privilege elevation & permission-denied simulation tests
└── ezcli_app/
    ├── __init__.py        # Package version (__version__ = "0.3.0")
    ├── config.py          # Declarative FeatureTemplate definitions & aliases
    ├── distro.py          # /etc/os-release parsing and Debian validation
    ├── emoji.py           # Font capability and UTF-8 detection
    ├── collectors.py      # Subprocess execution and multi-platform queries
    ├── renderers.py       # Rich visual layout and box-drawing renderers
    ├── menu.py            # Interactive TUI menu and keyboard navigation
    ├── main.py            # Subcommand parser, visual choose-directory dispatcher
    ├── elevation.py       # Shared privilege-elevation layer & password UX (v0.3)
    ├── privileged_helper.py# Minimal privileged helper for elevated tasks
    ├── file_engine.py     # Safe file operations, SHA256 checks, conflict policies
    ├── file_cli.py        # Interactive copy, move, paste, and undo CLI handlers
    ├── create_cli.py      # Interactive create-folder and create-file handlers (v0.3)
    ├── delete_cli.py      # Safe consent-first delete CLI handlers (v0.3)
    ├── edit_cli.py        # Modern text & code editor CLI handlers (v0.3)
    ├── undo.py            # Reversible undo history engine (~/.local/share/ez)
    ├── editor/            # Textual TUI Mini Text & Code Editor (v0.3)
    │   ├── __init__.py    # Editor package exports
    │   └── editor_app.py  # Syntax highlighting, line numbers, modals & auto-elevation
    └── explorer/          # Textual TUI File Explorer with lock-emoji integration
        ├── file_icons.py  # Emoji mapping per file extension and MIME type
        ├── places.py      # Bookmarks and standard quick places
        └── explorer_app.py# Reusable file manager, pickers, and elevation reload
```

---

## 📜 Version Milestones & History

- **v0.1 — Read-Only System Diagnostics & Universal Package Search**:
  - 12 read-only system diagnostic subcommands (`system-info`, `stats`, `disk-info`, `big-files`, `network-info`, `logs`, etc.).
  - Cross-platform package management queries for **APT 📦**, **Flatpak 🟣**, and **Snap 🟢**.
  - Interactive Rich terminal menu with full keyboard and mouse support.
- **v0.2 — Modern File Management & Reversible Undo**:
  - Graphical terminal file explorer (`ez choose-directory`) with search, places, bookmarks, and subshell launcher.
  - Multi-select visual `copy` and `move` operations.
  - Previewed `paste` with conflict resolution (`ask`, `skip`, `overwrite`, `rename`) and progress bars.
  - Reversible `undo` and `redo` transaction engine.
- **v0.3 — Safe Creation, Deletion, Mini Editor & Automatic Elevation**:
  - Pure modern creation commands (`ez create-folder`, `ez create-file`) replacing legacy commands (`mkdir`, `touch`), directly or visually via mini explorer (`[n]`).
  - Consent-first deletion (`ez delete`, `ez delete choose-directory`) replacing dangerous `rm` / `rm -rf`.
  - Modern terminal text and code editor (`ez edit-file`) replacing `nano`/`vi` with Tree-sitter syntax highlighting, line numbers, find search, and unsaved changes guard.
  - Non-force-first safety: non-empty folders always prompt before any force removal. Direct commands restricted to current directory.
  - Dedicated deletion and file editing picker modes so regular directory browsing remains 100% clean and isolated.
  - 100% automatic privilege elevation with consent and visible dot password feedback (`••••`), without `--admin` flags or root contamination.

---

## 🧪 Running Tests

To run the automated unit test suite:
```bash
python3 -m unittest discover tests/
```

All 103 unit tests validate distro detection, collector safety, file operations, conflict policies, cross-filesystem moves, undo engine, command parsing, file/folder creation, safe deletion with force prompts, mini text editor validation, binary file protection, permission-denied simulations, and the privilege elevation layer.
