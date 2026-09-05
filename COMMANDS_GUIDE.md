# 📖 EasyCLI (`ez`) Complete Commands Guide & Linux Command Replacement Map

EasyCLI (`ez`) provides beginner-friendly, visually rich, and interactive modern alternatives to traditional Linux terminal commands. Instead of memorizing obscure flags, cryptic syntax, or risk-prone bash utilities, EasyCLI presents clean colored cards, live visual monitors, interactive file managers, and reversible safety mechanisms.

---

## 💡 Universal Dual-Mode Architecture for File Commands

Every file management command in EasyCLI (`copy`, `move`, `paste`, `delete`, `edit-file`, `create-folder`, `create-file`, and `big-files`) follows a consistent **Dual-Mode System**:

1. **Direct Mode (Current Directory)**:
   - For fast, immediate actions in your current working directory without any popup windows.
   - Syntax: `ez <command> <filename.ext>` or `ez <command> <folder_name/>`.
2. **Visual System-Wide Mode (`choose-directory`)**:
   - For browsing, inspecting, and selecting files or folders **anywhere across the entire system** (such as `/`, `/etc`, `/var`, `/home`, external drives, USB mounts).
   - Syntax: `ez <command> choose-directory` (or omit arguments to automatically launch the picker).

---

## 🗺️ Complete Command Replacement Matrix

| # | EasyCLI Command & Aliases | Traditional Linux Command(s) Replaced | Primary Value Add & Safety Improvements |
| :-: | :--- | :--- | :--- |
| 1 | `ez system-info` | `hostnamectl`, `uptime -p`, `/etc/os-release`, `uname -r`, `arch` | Single formatted card with OS, kernel, hostname, architecture, and uptime without running 4 separate commands. |
| 2 | `ez stats` | `htop`, `top`, `free -h`, `uptime`, `nproc`, `ps aux`, `kill` | Modern live Textual monitor with per-core CPU bars, RAM/Swap meters, instant search filtering (`/`), and safe GUI-style kill confirmation with auto-elevation. |
| 3 | `ez disk-info` | `df -h` | Eliminates screen clutter from pseudo-filesystems (loop, tmpfs, udev); displays physical storage drives with colored inline usage bars. |
| 4 | `ez big-files [dir \| choose-directory]` | `du -h --max-depth=1 \| sort -hr \| head -n 10`, `find` | Replaces long shell pipelines with an animated scanner spinner, formatted size table, and visual folder picker. |
| 5 | `ez logs [N]` | `journalctl -n N --no-pager`, `dmesg` | Color-codes error logs in red, warnings in yellow, and info logs in green. |
| 6 | `ez choose-directory [path]`<br>*(Aliases: `ez choose`, `ez explorer`)* | `ranger`, `mc`, `cd`, `ls -la`, `xdg-open` | Full graphical terminal file manager with mouse support, file emojis, bookmarks, and a subshell launcher (`o`) or path output (`-p`). |
| 7 | `ez copy [target \| choose-directory]` | `cp -r <src> <dest>` | Desktop-style clipboard staging (current directory directly, or anywhere visually) without needing destination upfront; includes collision detection and undo logging. |
| 8 | `ez move [target \| choose-directory]` | `mv <src> <dest>` | Reversible cut-and-paste with collision resolution and automatic rollback. |
| 9 | `ez paste [choose-directory]` | *(No direct CLI equivalent — GUI clipboard)* | Pastes staged clipboard files into the current folder or a visually selected destination with conflict resolution (Overwrite, Auto-Rename, Skip). |
| 10 | `ez undo` | *(No native bash equivalent — lost data)* | One-click rollback for the most recent paste operation (restores overwritten files and reverses moves). |
| 11 | `ez redo` | *(No native bash equivalent)* | Re-applies the most recently undone operation with safety checks. |
| 12 | `ez create-folder [name] [choose-directory]`<br>*(Alias: `ez new-folder`)* | `mkdir -p <name>` | Validates folder names, detects existing folders, and allows creating directly or picking the target directory visually with auto-elevation. |
| 13 | `ez create-file [name] [choose-directory]`<br>*(Alias: `ez new-file`)* | `touch <name>` | Validates file extensions, prevents accidental overwrites, and supports visual destination selection with auto-elevation. |
| 14 | `ez delete [target \| choose-directory]`<br>*(Aliases: `ez del`, `ez remove`)* | `rm -rf <target>`, `rmdir <target>` | Prevents catastrophic mistakes: non-force check first, displays item summary, requires explicit confirmation, and handles safe auto-elevation. |
| 15 | `ez edit-file [target \| choose-directory]` | `nano`, `vim`, `micro`, `gedit`, `sudoedit` | Modern code & text editor with syntax highlighting for 15+ languages, visual find & replace (`Ctrl+F`), and automatic elevated saving for protected system files. |
| 16 | `ez package-search <kw>` | `apt search`, `flatpak search`, `snap find` | Unified search across **APT 📦**, **Flatpak 🟣**, and **Snap 🟢** with one-click platform installation commands. |
| 17 | `ez package <name>` | `apt show <name>`, `dpkg -s <name>` | Clean summary card showing version, size, homepage, description, and installed status without walls of text. |
| 18 | `ez available-updates` | `apt list --upgradable` | Read-only summary table of available upgrades without modifying system lists or running unexpected updates. |
| 19 | `ez installed-packages`<br>*(Alias: `ez installed`)* | `apt list --installed`, `dpkg-query -l`, `flatpak list`, `snap list` | Comprehensive list of installed software across system packages and desktop applications without truncation. |
| 20 | `ez installed-package-search <kw>` | `apt list --installed \| grep -i <kw>` | Fast case-insensitive search through installed system software without complex bash regex. |
| 21 | `ez service-status <name>` | `systemctl status <name>`, `is-active`, `is-enabled` | Compact card with clear running state (Active/Inactive) and boot startup state (Enabled/Disabled). |
| 22 | `ez network-info` | `ip -br addr`, `ip route`, `/etc/resolv.conf`, `ping` | Consolidates IP addresses, interfaces, default gateway, DNS servers, and Internet connectivity into one card. |
| 23 | `ez` *(no args)* | *(Manual CLI navigation)* | Full interactive TUI menu with searchable categories, emoji icons, and hotkey navigation. |
| 24 | `ez help`<br>*(Flags: `-h`, `--help`)* | `man <tool>`, `<tool> --help` | Formatted overview of all subcommands, arguments, and safety guidelines. |
| 25 | `ez version`<br>*(Flags: `-v`, `--version`)* | `<tool> --version`, `<tool> -v` | Displays application version and safe elevation status. |

---

## 🛠️ In-Depth Command Reference

### 1. System Monitoring & Diagnostics

#### `ez system-info`
- **Replaces:** `hostnamectl`, `uptime -p`, `/etc/os-release`, `uname -r`, `arch`
- **Why it's better:** Aggregates OS release, version, codename, desktop environment, kernel release, machine architecture, hostname, and human-readable uptime into a single formatted card.
- **Syntax:**
  ```bash
  ez system-info
  ```
- **Example Output:**
  ```
  ╭─────────────────────── 💻 System Information ────────────────────────╮
  │   OS Distribution     Deepin 25 (rolling)                           │
  │   Kernel Version      6.18.38-amd64-desktop                         │
  │   Hostname            shaheer-PC                                    │
  │   Architecture        x86_64                                        │
  │   System Uptime       up 9 hours, 14 minutes                        │
  ╰─────────────────────────────────────────────────────────────────────╯
  ```

---

#### `ez stats`
- **Replaces:** `htop`, `top`, `free -h`, `uptime`, `nproc`, `ps aux`, `kill`
- **Why it's better:** Launches a modern, live-updating Textual TUI system and process monitor. Features per-core visual CPU bars, RAM/Swap gauge meters, instant search filtering (`/`), column sorting (`s`), process inspection (`i`), and safe process termination (`k`) with automatic admin elevation for system daemons.
- **Interactive Controls:**
  - `k` / `x`: Terminate process (Safe `SIGTERM` or Force `SIGKILL`).
  - `i` / `Enter`: Detailed process inspection (CWD, open files, binary path, cmdline).
  - `/` or `Ctrl+F`: Search / filter processes in real-time.
  - `s`: Open Sort Picker (Sort by CPU%, Memory%, PID, Resident RAM, or Name).
  - `Space`: Pause / Resume live stats updating.
  - `+` / `-`: Speed up or slow down refresh rate (0.5s to 5.0s).
  - `q` / `Esc`: Exit monitor.
- **Syntax:**
  ```bash
  ez stats
  ```
- **Scripting / Non-Interactive Fallback:**
  When piped (e.g. `ez stats | cat`) or run in test scripts, outputs a static Rich card with CPU load and RAM/Swap meters.

---

#### `ez disk-info`
- **Replaces:** `df -h`
- **Why it's better:** Standard `df -h` pollutes the terminal with dozens of irrelevant pseudo-filesystems (loop mounts, squashfs, tmpfs, udev). `ez disk-info` filters these out automatically, displaying only physical and persistent storage drives with colored inline usage bars.
- **Syntax:**
  ```bash
  ez disk-info
  ```

---

#### `ez big-files [folder | choose-directory]`
- **Replaces:** `du -h --max-depth=1 <folder> | sort -hr | head -n 10`, `find`
- **Why it's better:** Replaces long, error-prone shell pipelines with an animated scanner spinner, formatted size table, and visual folder picker.
- **Syntax:**
  ```bash
  # Mode 1: Direct Scan
  ez big-files                  # Scans home directory (~)
  ez big-files /var/log         # Scans specific folder

  # Mode 2: Visual Explorer Scan
  ez big-files choose-directory # Picks directory visually from anywhere
  ```

---

#### `ez logs [N]`
- **Replaces:** `journalctl -n N --no-pager`, `dmesg`
- **Why it's better:** Standard `journalctl` dumps unformatted monochrome text. `ez logs` color-codes lines by severity: errors in bold red, warnings in yellow, and operational notices in green.
- **Syntax:**
  ```bash
  ez logs       # Shows latest 50 lines (default)
  ez logs 100   # Shows latest 100 lines
  ```

---

### 2. File & Directory Management (Visual + Direct)

#### `ez choose-directory [path]`
*(Aliases: `ez choose`, `ez explorer`)*
- **Replaces:** `ranger`, `mc`, `cd`, `ls -la`, `xdg-open`
- **Why it's better:** A full graphical terminal file manager built with Textual. Includes full mouse support, single-character file type emojis, bookmarks (Home, Documents, Downloads, Desktop), file details, hidden files toggle (`.`), and a subshell launcher (`o`) that drops you directly into any folder.
- **Syntax:**
  ```bash
  ez choose-directory           # Opens in current folder
  ez choose-directory ~         # Opens in Home directory
  ez choose-directory /var/log  # Opens in specific folder
  ez choose-directory -p        # Prints selected directory to stdout (ideal for shell integration)
  ```
- **Shell `cd` Integration:**
  ```bash
  cd "$(ez choose -p)"
  ```

---

#### `ez copy [target | choose-directory]`
- **Replaces:** `cp -r <src> <dest>`
- **Why it's better:** Implements desktop-style 2-stage clipboard staging. You stage files or folders first, then paste them anywhere with automatic collision handling and reversible undo.
- **Syntax:**
  ```bash
  # Mode 1: Direct Current-Directory Staging (Instant, No TUI)
  ez copy document.txt          # Stages a single file in current directory
  ez copy my_folder/            # Stages a folder in current directory

  # Mode 2: System-Wide Visual Selection (Browse Anywhere)
  ez copy choose-directory      # Opens explorer to browse and pick files/folders from anywhere
  ez copy                       # (Without arguments, launches the visual picker)
  ```

---

#### `ez move [target | choose-directory]`
- **Replaces:** `mv <src> <dest>`
- **Why it's better:** Implements reversible cut-and-paste staging with collision detection and automated rollback.
- **Syntax:**
  ```bash
  # Mode 1: Direct Current-Directory Staging (Instant, No TUI)
  ez move document.txt          # Stages a file to move
  ez move my_folder/            # Stages a folder to move

  # Mode 2: System-Wide Visual Selection (Browse Anywhere)
  ez move choose-directory      # Opens explorer to pick items from any directory
  ez move                       # (Without arguments, launches the visual picker)
  ```

---

#### `ez paste [choose-directory]`
- **Replaces:** GUI desktop clipboard paste
- **Why it's better:** Pastes staged files/folders with safety pre-checks:
  1. Shows itemized summary of what will be copied or moved.
  2. Automatic collision detection (Option to Skip, Overwrite, or Auto-Rename).
  3. Safe permission elevation if pasting into a write-protected directory (e.g. `/etc` or `/var`).
  4. Automatic undo log registration so changes can be reverted instantly.
- **Syntax:**
  ```bash
  # Mode 1: Paste into Current Directory (Instant, No TUI)
  ez paste

  # Mode 2: Paste into Any Chosen Destination (Visual Picker)
  ez paste choose-directory
  ```

---

#### `ez undo` & `ez redo`
- **Replaces:** *(No native Linux CLI equivalent!)*
- **Why it's better:** Linux `cp` and `mv` have no undo feature — if you misplace files or overwrite something, recovery is difficult or impossible. `ez undo` provides a 1-step reversible rollback with backup recovery.
- **Syntax:**
  ```bash
  ez undo   # Reverts the most recent paste operation
  ez redo   # Re-applies the operation
  ```

---

#### `ez create-folder [name] [choose-directory]`
*(Alias: `ez new-folder`)*
- **Replaces:** `mkdir -p <name>`
- **Why it's better:** Validates naming, detects existing folders, supports visual destination selection, and automatically elevates privileges if creating in a protected system path.
- **Syntax:**
  ```bash
  # Mode 1: Create in Current Directory
  ez create-folder Projects

  # Mode 2: Create in Any Chosen Location Visually
  ez create-folder Projects choose-directory
  ez create-folder choose-directory
  ```

---

#### `ez create-file [name] [choose-directory]`
*(Alias: `ez new-file`)*
- **Replaces:** `touch <name>`
- **Why it's better:** Validates file extensions, prevents accidental overwriting of existing files, supports visual destination selection, and automatically elevates privileges if creating in protected directories.
- **Syntax:**
  ```bash
  # Mode 1: Create in Current Directory
  ez create-file script.py

  # Mode 2: Create in Any Chosen Location Visually
  ez create-file script.py choose-directory
  ez create-file choose-directory
  ```

---

#### `ez delete [target | choose-directory]`
*(Aliases: `ez del`, `ez remove`)*
- **Replaces:** `rm -rf <target>`, `rmdir <target>`
- **Why it's better:** Traditional `rm -rf` has caused countless catastrophic data losses. `ez delete`:
  1. Non-force first: Warns if folder is non-empty before proceeding.
  2. Displays confirmation card showing exact items and total size.
  3. Prompts for explicit user confirmation (`[y/N]`).
  4. Safe auto-elevation if deleting protected root files.
- **Syntax:**
  ```bash
  # Mode 1: Direct Deletion in Current Directory
  ez delete file.txt
  ez delete old_folder/

  # Mode 2: Visual Selection Anywhere on System
  ez delete choose-directory
  ez delete                      # (Without arguments, launches visual picker)
  ```

---

#### `ez edit-file [target | choose-directory]`
- **Replaces:** `nano`, `vim`, `micro`, `gedit`, `sudoedit`
- **Why it's better:** A full modern terminal text & code editor with syntax highlighting for 15+ languages (Python, JS/TS, Bash, Markdown, HTML, CSS, Rust, Go, SQL, JSON, YAML). Includes mouse support, visual Find & Replace (`Ctrl+F`), line jumping (`Ctrl+G`), soft word wrap (`Ctrl+W`), and automated elevation when editing protected configuration files (like `/etc/hosts` or `/etc/fstab`).
- **Syntax:**
  ```bash
  # Mode 1: Edit File in Current Directory
  ez edit-file config.yaml
  ez edit-file script.py

  # Mode 2: Navigate and Edit File Anywhere on System
  ez edit-file choose-directory  # Opens visual explorer to pick any file (e.g. in /etc, ~, /var)
  ez edit-file                   # (Without arguments, launches visual picker)
  ```

---

### 3. Package & Software Management

#### `ez package-search <keyword>`
- **Replaces:** `apt search <kw>`, `flatpak search <kw>`, `snap find <kw>`
- **Why it's better:** Searches across **APT**, **Flatpak**, and **Snap** simultaneously. Displays an interactive platform picker and presents exact installation commands ready to run.
- **Syntax:**
  ```bash
  ez package-search vlc
  ez package-search vscode
  ```

---

#### `ez package <name>`
- **Replaces:** `apt show <name>`, `dpkg -s <name>`
- **Why it's better:** Parses the noisy multiline output of `apt show` into a clean, structured package summary card showing installed status, version, download size, architecture, homepage, and description.
- **Syntax:**
  ```bash
  ez package curl
  ez package nginx
  ```

---

#### `ez available-updates`
- **Replaces:** `apt list --upgradable`
- **Why it's better:** Formats upgradable packages into a clean table with old vs. new version numbers. Strictly read-only: never modifies package lists or triggers unwanted updates.
- **Syntax:**
  ```bash
  ez available-updates
  ```

---

#### `ez update`
- **Replaces:** `apt update`, `apt-get update`
- **Why it's better:** Provides a friendly, strictly read-only repository catalog refresh. Shows an explanation card, asks for consent, and prompts for admin authentication with visible dot feedback (`●●●●`). After updating, summarizes how many packages can be upgraded and tolerates repository warnings (like expired PPA keys) without crashing. Concludes with a reassuring anti-panic note: *"This was only an information refresh — nothing was installed. You do not need to run this repeatedly."*
- **Syntax:**
  ```bash
  ez update
  ```

---

#### `ez upgrade`
- **Replaces:** `apt upgrade`, `apt-get upgrade`, `snap refresh`, `flatpak update`
- **Why it's better:** Orchestrates a comprehensive multi-source system upgrade under a single elevation consent. First refreshes lists, then builds an impact simulation preview (packages to upgrade, download size, disk delta, kept-back packages). Evaluates risk level (Medium vs. High), recommends a Timeshift snapshot if installed, prompts for explicit confirmation, runs non-destructive upgrades sequentially, checks `/var/run/reboot-required`, and ends with: *"Done. Run this only when you choose to — there is no daily obligation."*
- **Syntax:**
  ```bash
  ez upgrade
  ```

---

#### `ez installed-packages`
*(Alias: `ez installed`)*
- **Replaces:** `apt list --installed`, `dpkg-query -l`, `flatpak list`, `snap list`
- **Why it's better:** Lists all installed system software across APT and desktop sandboxes without truncating names or requiring complex piping.
- **Syntax:**
  ```bash
  ez installed-packages
  ez installed
  ```

---

#### `ez installed-package-search <name>`
- **Replaces:** `apt list --installed | grep -i <name>`, `dpkg-query -l | grep -i <name>`
- **Why it's better:** Fast, case-insensitive search through installed system software without complex bash regex or grep pipelines.
- **Syntax:**
  ```bash
  ez installed-package-search python
  ez installed-package-search vlc
  ```

---

### 4. Services & Networking

#### `ez service-status <name>`
- **Replaces:** `systemctl status <name>`, `systemctl is-active`, `systemctl is-enabled`
- **Why it's better:** Eliminates noisy multi-page systemd status outputs. Shows a compact card with clear running state (Active/Inactive), boot startup state (Enabled/Disabled), and friendly recommendations.
- **Syntax:**
  ```bash
  ez service-status ssh
  ez service-status docker
  ```

---

#### `ez network-info`
- **Replaces:** `ip -br addr`, `ip route`, `cat /etc/resolv.conf`, `ping -c 1`
- **Why it's better:** Traditional network checks require running multiple separate commands. `ez network-info` consolidates local IP addresses, MAC addresses, interface states, default gateway, DNS resolvers, and internet reachability into one visual overview.
- **Syntax:**
  ```bash
  ez network-info
  ```

---

### 5. Interactive Navigation & Global Options

#### `ez` *(No Arguments)*
- **Replaces:** Manual command memorization
- **Why it's better:** Launches the EasyCLI interactive terminal menu with categories, emoji icons, command descriptions, and keyboard shortcuts (`[b]` Back, `[r]` Refresh, `[q]` Quit).
- **Syntax:**
  ```bash
  ez
  ```

---

#### `ez help`
*(Flags: `-h`, `--help`)*
- **Replaces:** `man <tool>`, `<tool> --help`
- **Why it's better:** Outputs a clean, categorized table of all subcommands, arguments, and practical examples.
- **Syntax:**
  ```bash
  ez help
  ez --help
  ez -h
  ```

---

#### `ez version`
*(Flags: `-v`, `--version`)*
- **Replaces:** `<tool> --version`, `<tool> -v`
- **Why it's better:** Displays application version and safe elevation status.
- **Syntax:**
  ```bash
  ez version
  ez --version
  ez -v
  ```
