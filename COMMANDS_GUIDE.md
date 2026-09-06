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

| # | EasyCLI Command (Flagless) | Traditional Linux Command(s) Replaced | Primary Value Add & Safety Improvements |
| :-: | :--- | :--- | :--- |
| 1 | `ez system-info` | `hostnamectl`, `uptime -p`, `/etc/os-release`, `uname -r`, `arch` | Single formatted card with OS, kernel, hostname, architecture, and uptime without running 4 separate commands. |
| 2 | `ez stats` | `htop`, `top`, `free -h`, `uptime`, `nproc`, `ps aux`, `kill` | Modern live Textual monitor with per-core CPU bars, RAM/Swap meters, instant search filtering (`/`), and safe GUI-style kill confirmation with auto-elevation. |
| 3 | `ez task-manager` | *(Windows Task Manager)*, `ps`, `kill` | Lite & modern Windows-style task manager for user apps with full mouse support, rich emoji icons, unresponsive app detection (`⚠️ Unresponsive`), and one-click termination. |
| 4 | `ez task-manager-pro` | `ps aux`, `top`, `sudo kill` | Comprehensive pro task manager displaying all user apps, background daemons, and system services with category tabs (`[All]`, `[Apps]`, `[Background]`, `[System]`, `[Unresponsive]`) and automatic admin elevation. |
| 5 | `ez disk-info` | `df -h` | Eliminates screen clutter from pseudo-filesystems (loop, tmpfs, udev); displays physical storage drives with colored inline usage bars. |
| 6 | `ez big-files [dir \| choose-directory]` | `du -h --max-depth=1 \| sort -hr \| head -n 10`, `find` | Replaces long shell pipelines with an animated scanner spinner, formatted size table, and visual folder picker. |
| 7 | `ez logs [N]` | `journalctl -n N --no-pager`, `dmesg` | Color-codes error logs in red, warnings in yellow, and info logs in green. |
| 8 | `ez choose-directory [path]` | `ranger`, `mc`, `cd`, `ls -la`, `xdg-open` | Full graphical terminal file manager with mouse support, file emojis, bookmarks, and a subshell launcher (`o`). |
| 9 | `ez copy [target \| choose-directory]` | `cp -r <src> <dest>` | Desktop-style clipboard staging (current directory directly, or anywhere visually) without needing destination upfront; includes collision detection and undo logging. |
| 10 | `ez move [target \| choose-directory]` | `mv <src> <dest>` | Reversible cut-and-paste with collision resolution and automatic rollback. |
| 11 | `ez paste [choose-directory]` | *(No direct CLI equivalent — GUI clipboard)* | Pastes staged clipboard files into the current folder or a visually selected destination with conflict resolution (Overwrite, Auto-Rename, Skip). |
| 12 | `ez undo` | *(No native bash equivalent — lost data)* | One-click rollback for the most recent paste operation (restores overwritten files and reverses moves). |
| 13 | `ez redo` | *(No native bash equivalent)* | Re-applies the most recently undone operation with safety checks. |
| 14 | `ez create-folder [name] [choose-directory]` | `mkdir -p <name>` | Validates folder names, detects existing folders, and allows creating directly or picking the target directory visually with auto-elevation. |
| 15 | `ez create-file [name] [choose-directory]` | `touch <name>` | Validates file extensions, prevents accidental overwrites, and supports visual destination selection with auto-elevation. |
| 16 | `ez delete [target \| choose-directory]` | `rm -rf <target>`, `rmdir <target>` | Prevents catastrophic mistakes: non-force check first, displays item summary, requires explicit confirmation, and handles safe auto-elevation. |
| 17 | `ez edit-file [target \| choose-directory]` | `nano`, `vim`, `micro`, `gedit`, `sudoedit` | Modern code & text editor with syntax highlighting for 15+ languages, visual find & replace (`Ctrl+F`), and automatic elevated saving for protected system files. |
| 18 | `ez package-search <kw>` | `apt search`, `flatpak search`, `snap find` | Unified search across **APT 📦**, **Flatpak 🟣**, and **Snap 🟢**; merges duplicates into one item with source badges and directly installs selected packages with automated elevation. |
| 19 | `ez package <name>` | `apt show <name>`, `dpkg -s <name>` | Clean summary card showing version, size, homepage, description, and installed status without walls of text. |
| 20 | `ez available-updates` | `apt list --upgradable` | Read-only summary table of available upgrades without modifying system lists or running unexpected updates. |
| 21 | `ez update` | `apt update`, `apt-get update` | Refresh package catalog only, with consent, dot password feedback, warning tolerance, and anti-panic reminders. |
| 22 | `ez upgrade` | `apt upgrade`, `flatpak update`, `snap refresh` | Multi-source safe system upgrade under single elevation consent with simulation preview, risk badge, Timeshift restore point, and reboot check. |
| 23 | `ez uninstall <name>` | `apt remove`, `flatpak uninstall`, `snap remove` | Safe application uninstallation across APT, Flatpak, and Snap with pre-removal warning card, single consent, and zero-cache admin elevation. |
| 24 | `ez installed-packages` | `apt list --installed`, `dpkg-query -l`, `flatpak list`, `snap list` | Comprehensive list of installed software across system packages and desktop applications without truncation. |
| 25 | `ez installed-package-search <kw>` | `apt list --installed \| grep -i <kw>` | Fast case-insensitive search through installed system software without complex bash regex. |
| 26 | `ez service-status <name>` | `systemctl status <name>`, `is-active`, `is-enabled` | Compact card with clear running state (Active/Inactive) and boot startup state (Enabled/Disabled). |
| 27 | `ez network-info` | `ip -br addr`, `ip route`, `/etc/resolv.conf`, `ping` | Consolidates IP addresses, interfaces, default gateway, DNS servers, and Internet connectivity into one card. |
| 28 | `ez` *(no args)* | *(Manual CLI navigation)* | Full interactive TUI menu with searchable categories, emoji icons, and hotkey navigation. |
| 29 | `ez help` | `man <tool>`, `<tool> --help` | Formatted overview of all subcommands, arguments, and safety guidelines. |
| 30 | `ez version [name]` | `<tool> --version`, `dpkg -s`, `apt-cache policy`, `snap list`, `flatpak info`, `pip show`, `npm list` | Universal version checker: without arguments, prints EasyCLI version + hint; with `<name>`, auto-detects version across binary on PATH, Debian package, APT catalog, Snap, Flatpak, Python library, and Node.js library in a single clean card. |
| 31 | `ez check-internet` | `ping`, `traceroute`, `host`, `dig`, `curl -I` | 3-stage connectivity test across local router, DNS resolvers, and internet reachability. Shows a visual pipeline with latency (`✔`/`✖`) and an immediate "Why internet isn't working" one-line diagnostic reply. |
| 32 | `ez connect-wifi` | `nmcli dev wifi`, `nmtui`, `iwconfig`, `wpa_supplicant` | In-terminal graphical Wi-Fi manager with mouse support, signal bars, network scanning, password entry modal with show/hide toggle, and action buttons (`Connect`, `Cancel`, `Refresh`, `Disconnect`). |
| 33 | `ez search-file <term>` | `find / -iname "*name*"`, `locate`, `fzf` | Fast fuzzy file search starting from `/home`, rich results table with emoji icons, interactive selection to open, copy path, or edit, and optional system-wide (`'/'`) fallback with auto-elevation. |

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

#### `ez task-manager`
- **Replaces:** Windows Task Manager, `ps`, `kill`, `killall`
- **Why it's better:** Modern, lightweight terminal Task Manager modeled after Windows Task Manager with full mouse support and rich emoji icons. Filters out confusing system daemons and kernel threads to display only your active **User Applications** (browsers, editors, terminals, media players). Automatically detects **unresponsive / hung processes** (`⚠️ Unresponsive`) and provides one-click safe termination (`End Task` / `Force Kill`).
- **Interactive Controls:**
  - `Click row`: Select process.
  - `Click column headers`: Sort by CPU%, Memory%, Name, PID, or Status.
  - `Del` / `k`: End Task (Graceful `SIGTERM` with safety confirmation).
  - `Shift+K`: Force Kill (Immediate `SIGKILL`).
  - `/`: Search / filter processes in real-time.
  - `p`: Switch to Pro Mode (`ez task-manager-pro`).
  - `i` / `Enter`: Detailed process inspection.
  - `Space`: Pause / Resume live polling.
  - `q` / `Esc`: Exit.
- **Syntax:**
  ```bash
  ez task-manager
  ```

---

#### `ez task-manager-pro`
- **Replaces:** `top`, `htop`, `ps aux`, `sudo kill`
- **Why it's better:** The comprehensive administrator version of the Task Manager. Shows all programs from normal mode plus **background daemons and system services** (`📱 Apps`, `⚙️ Background`, `🔒 System`). Includes category tabs (`[All]`, `[Apps]`, `[Background]`, `[System]`, `[Unresponsive]`). When terminating system or root processes, **admin consent is handled automatically** via the elevation layer without having to launch the app as root.
- **Syntax:**
  ```bash
  ez task-manager-pro
  ```

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
- **Replaces:** `ranger`, `mc`, `cd`, `ls -la`, `xdg-open`
- **Why it's better:** A full graphical terminal file manager built with Textual. Includes full mouse support, single-character file type emojis, bookmarks (Home, Documents, Downloads, Desktop), file details, hidden files toggle (`.`), and a subshell launcher (`o`) that drops you directly into any folder.
- **Syntax:**
  ```bash
  ez choose-directory           # Opens in current folder
  ez choose-directory ~         # Opens in Home directory
  ez choose-directory /var/log  # Opens in specific folder
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
- **Why it's better:** Searches across **APT**, **Flatpak**, and **Snap** simultaneously. Automatically merges results sharing the same name into a single entry with multi-source badges (`📦 APT  🟣 Flatpak  🟢 Snap`), lets you pick which source to install from, and installs the software directly with automated elevation.
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

#### `ez uninstall <name>`
- **Replaces:** `apt remove <name>`, `flatpak uninstall <name>`, `snap remove <name>`
- **Why it's better:** Unified software removal across **APT**, **Flatpak**, and **Snap**. Automatically resolves whether an application is installed as a system package or desktop container. Displays a clear pre-removal warning card (package details, occupied disk space, and impact notice). Requires a single explicit confirmation prompt followed by dot-masked admin password authentication (`●●●●`). Strictly **never stores or caches your admin credentials**.
- **Syntax:**
  ```bash
  ez uninstall vlc
  ez uninstall gimp
  ```

---

#### `ez installed-packages`
- **Replaces:** `apt list --installed`, `dpkg-query -l`, `flatpak list`, `snap list`
- **Why it's better:** Lists all installed system software across APT and desktop sandboxes without truncating names or requiring complex piping.
- **Syntax:**
  ```bash
  ez installed-packages
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

#### `ez check-internet`
- **Replaces:** `ping <gateway>`, `host google.com`, `ping 1.1.1.1`, `traceroute`, `curl -I`
- **Why it's better:** Replaces cumbersome multi-step troubleshooting commands with a single instant diagnostic. Checks router ping, DNS resolution, and public internet reachability, displaying a high-contrast visual pipeline with precise latency and an immediate one-line explanation of *"Why internet isn't working"*.
- **Visual Pipeline:**
  ```
  Router ✔ (1.6 ms) ➔ DNS ✔ (24.3 ms) ➔ Internet ✔ (26.2 ms)
  ```
- **"Why internet isn't working" Diagnostics:**
  - If router ping fails: Identifies whether local Wi-Fi/Ethernet is disconnected or the router is unresponsive.
  - If DNS fails: Pinpoints DNS resolver failure and advises checking DNS settings.
  - If internet reachability fails: Detects ISP outages, disconnected WAN cables, or captive portal blocks.
  - If all systems pass: Reassures the user that their internet connection is active and healthy.
- **Syntax:**
  ```bash
  ez check-internet
  ```

---

#### `ez connect-wifi`
- **Replaces:** `nmcli dev wifi connect`, `nmtui`, `wpa_passphrase`, `iwconfig`, `wpa_supplicant`
- **Why it's better:** Replaces complex and awkward wireless command syntax with a full, modern, in-terminal Wi-Fi application featuring full mouse support, real-time signal bars (`▂▄▆█ 85% 📶`), security detection (`🔒 WPA2/WPA3` / `🔓 Open`), password entry modal with show/hide toggle (`👁️` / `🙈`), and action buttons (`🔗 Connect`, `❌ Cancel`, `🔄 Refresh`, `🚫 Disconnect`).
- **Features & Controls:**
  - **Mouse Support:** Click any network row to select, double-click to connect directly, and click bottom toolbar buttons.
  - **Password Dialog:** Modal dialog with masked password input and an `👁️ Show Password` / `🙈 Hide Password` toggle button so users can verify typos before connecting.
  - **Action Toolbar:** `[c]` / `[🔗 Connect]`, `[r]` / `[🔄 Refresh]`, `[d]` / `[🚫 Disconnect]`, `[q]` / `[❌ Close]`.
  - **Search & Filter:** Press `[/]` to instantly search and filter Wi-Fi networks by name.
- **Syntax:**
  ```bash
  ez connect-wifi
  ```

---

### 5. Interactive Navigation & Global Commands (Flagless)

#### `ez` *(No Arguments)*
- **Replaces:** Manual command memorization
- **Why it's better:** Launches the EasyCLI interactive terminal menu with categories, emoji icons, command descriptions, and keyboard shortcuts (`[b]` Back, `[r]` Refresh, `[q]` Quit).
- **Syntax:**
  ```bash
  ez
  ```

---

#### `ez help`
- **Replaces:** `man <tool>`, `<tool> --help`
- **Why it's better:** Outputs a clean, categorized table of all subcommands, arguments, and practical examples.
- **Syntax:**
  ```bash
  ez help
  ```

---

#### `ez version [name]`
- **Replaces:** `<tool> --version`, `dpkg -s`, `apt-cache policy`, `snap list`, `flatpak info`, `pip show`, `npm list`
- **Why it's better:** One single, fully automatic, beginner-friendly version checker for any app, package, or library without needing any flags or type specifiers.
  - **No argument (`ez version`)**: Displays EasyCLI's own version and a one-line tip on how to check other items.
  - **With argument (`ez version <name>`)**: Automatically scans 7 sources in exact order:
    1. 🖥️ **Binary on PATH**: Quietly tries common version arguments and parses the first sane version string.
    2. 📦 **Debian Package (`dpkg`)**: Queries installed packages and installation timestamp.
    3. 📋 **APT Catalog**: Checks available repository candidate version.
    4. 🟢 **Snap Package**: Inspects installed Snap revisions and timestamps.
    5. 🟣 **Flatpak App**: Checks Flatpak application metadata and version.
    6. 🐍 **Python Library**: Queries Python package metadata via `importlib.metadata`.
    7. 📦 **Node.js Library**: Inspects global and local `package.json` files.
  - **Multi-Source Consolidation**: If a tool is installed via multiple systems (e.g. `curl` as both binary, Debian package, and Snap), all matches are displayed together in one clean card.
  - **Actionable Not-Found Guidance**: If nothing is found, provides friendly suggestions pointing to `ez package-search <name>` and `ez installed-packages`.
- **Syntax:**
  ```bash
  ez version            # Show EasyCLI version and usage hint
  ez version curl       # Inspect system app / binary / package
  ez version python3    # Check compiler or runtime version
  ez version rich       # Inspect Python library version
  ez version express    # Inspect Node.js library version
  ```

---

#### `ez search-file <term>`
- **Replaces:** `find / -iname "*name*"`, `locate <term>`, `fzf`
- **Why it's better:** Beginner-friendly fuzzy file finder that eliminates complicated `find` syntax and permission errors.
  - **Sequenced `/home` Search First:** Instantly scans `/home` without requiring root permissions.
  - **"Didn't Find What You Wanted?" Option:**
    - If 0 matches are found in `/home`, prompts: *"File not found in /home. Wanna look in whole system? '/' [y/N]"*.
    - Even if matches are found, provides a prominent `[s] 🌐 Search entire system ('/')` action in the menu so the user can easily expand the search if the file is outside `/home`.
  - **Safe Automatic Elevation:** When scanning `'/'`, automatically prompts for admin consent to search root-protected directories (`/etc`, `/var`, `/root`, `/opt`) while safely pruning virtual pseudo-filesystems (`/proc`, `/sys`, `/dev`).
  - **Interactive Action Menu:**
    - `[1] 📂 Open`: Launches the selected file in the system default application.
    - `[2] 📋 Copy path`: Copies the absolute file path to the clipboard and prints it clearly.
    - `[3] ✏️ Edit`: Opens the file in EasyCLI's integrated code and text editor.
    - `[q] ❌ Quit`: Clean exit.
- **Syntax:**
  ```bash
  ez search-file <term>
  ez search-file wifi_app.py
  ez search-file nginx.conf
  ez search-file report.pdf
  ```
