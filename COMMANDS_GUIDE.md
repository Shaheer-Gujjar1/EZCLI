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
| 14 | `ez create-folder [names...] [choose-directory]` | `mkdir -p <name>` | Validates folder names, prevents overwrites, supports single or comma-separated multiple folders in current directory, or picking visually with auto-elevation. |
| 15 | `ez create-file [names...] [choose-directory]` | `touch <name>` | Validates file extensions, prevents accidental overwrites, supports single or comma-separated multiple blank files in current directory, or picking visually. |
| 16 | `ez delete [target \| choose-directory]` | `rm -rf <target>`, `rmdir <target>` | Prevents catastrophic mistakes: non-force check first, displays item summary, requires explicit confirmation, and handles safe auto-elevation. |
| 17 | `ez edit-file [target \| choose-directory]` | `nano`, `vim`, `micro`, `gedit`, `sudoedit` | Modern code & text editor with syntax highlighting for 15+ languages, visual find & replace (`Ctrl+F`), and automatic elevated saving for protected system files. |
| 18 | `ez package-info [name]` | `apt show`, `apt search`, `flatpak search`, `snap find`, `pip`, `npm` | App-Store package inspector: checks local machine & stores simultaneously, loose matching, nature classification, safe actions (Run/Install/Uninstall), and App Hub menu when run without arguments. |
| 19 | `ez available-updates` | `apt list --upgradable` | Read-only summary table of available upgrades without modifying system lists or running unexpected updates. |
| 20 | `ez update` | `apt update`, `apt-get update` | Refresh package catalog only, with consent, dot password feedback, warning tolerance, and anti-panic reminders. |
| 21 | `ez upgrade` | `apt upgrade`, `flatpak update`, `snap refresh` | Multi-source safe system upgrade under single elevation consent with simulation preview, risk badge, Timeshift restore point, and reboot check. |
| 22 | `ez uninstall <name>` | `apt remove`, `flatpak uninstall`, `snap remove` | Safe application uninstallation across APT, Flatpak, and Snap with pre-removal warning card, single consent, and zero-cache admin elevation. |
| 23 | `ez list-installed-packages [apps\|packages\|both]` | `apt list --installed`, `dpkg-query -l`, `flatpak list`, `snap list`, `pip`, `npm` | List installed software with interactive filter (Installed Applications Only, Packages Only like npm/node/nala/php/pip, or Both). |
| 24 | `ez installed-package-search <kw>` | `apt list --installed \| grep -i <kw>` | Fast case-insensitive search through installed system software without complex bash regex. |
| 25 | `ez service-status <name>` | `systemctl status <name>`, `is-active`, `is-enabled` | Compact card with clear running state (Active/Inactive) and boot startup state (Enabled/Disabled). |
| 26 | `ez network-info` | `ip -br addr`, `ip route`, `/etc/resolv.conf`, `ping` | Consolidates IP addresses, interfaces, default gateway, DNS servers, and Internet connectivity into one card. |
| 27 | `ez` *(no args)* | *(Manual CLI navigation)* | Full interactive TUI menu with searchable categories, emoji icons, and hotkey navigation. |
| 28 | `ez help` | `man <tool>`, `<tool> --help` | Formatted overview of all subcommands, arguments, and safety guidelines. |
| 29 | `ez check-internet` | `ping`, `traceroute`, `host`, `dig`, `curl -I` | 3-stage connectivity test across local router, DNS resolvers, and internet reachability. Shows a visual pipeline with latency (`✔`/`✖`) and an immediate "Why internet isn't working" one-line diagnostic reply. |
| 30 | `ez connect-wifi` | `nmcli dev wifi`, `nmtui`, `iwconfig`, `wpa_supplicant` | In-terminal graphical Wi-Fi manager with mouse support, signal bars, network scanning, password entry modal with show/hide toggle, and action buttons (`Connect`, `Cancel`, `Refresh`, `Disconnect`). |
| 31 | `ez search-file <term>` | `find / -iname "*name*"`, `locate`, `fzf` | Fast fuzzy file search starting from `/home`, rich results table with emoji icons, interactive selection to open, copy path, or edit, and optional system-wide (`'/'`) fallback with auto-elevation. |
| 32 | `ez compress [targets \| choose-directory]` | `zip`, `tar -czf`, `tar -cJf`, `7z a`, `gzip`, `bzip2` | Interactive multi-format archive creator (`.zip`, `.tar.gz`, `.tar.xz`, `.7z`, `.tar.bz2`) with comma-separated targeting in current directory, mini explorer picker, live progress, and space-saved metrics. |
| 33 | `ez extract [archives...] [to <dest> \| choose-directory]` | `unzip`, `tar`, `7z` | Extract archive(s) into current directory (press Enter), specific destination (`to <path>`), visual picker (`to choose-directory`), or launch two-stage mini explorer. Automatic elevation for protected destinations. |
| 34 | `ez run [target \| choose-directory] [args...]` | `bash`, `python3`, `chmod +x && ./app`, `snap run`, `flatpak run`, `gio launch`, `./app.AppImage` | One universal command to execute any script, binary, AppImage, or launch apps. GUI apps launch detached keeping terminal free; CLI tools execute with flag-free Guided Mode and command preview. |
| 35 | `ez list [choose-directory]` | `ls`, `tree`, `du`, `stat` | Flagless and pathless unified directory listing and inspector. Instant pretty listing with background folder size streaming (Form 1) or visual directory picker with interactive TUI flat/tree toggle, sorting, hidden toggle, and plain English permissions details modal (Form 2). |


---

## 🛠️ In-Depth Command Reference

### 1. System Monitoring & Diagnostics

#### `ez system-info`
- **Replaces:** `hostnamectl`, `uptime -p`, `/etc/os-release`, `uname -r`, `arch`, `neofetch`, `fastfetch`
- **Why it's better:** Aggregates a comprehensive system dashboard including OS distribution, kernel, uptime, desktop environment, display server/resolution, shell, terminal, package counts, CPU specs, GPU(s), motherboard/BIOS, battery status, and inline RAM/Swap/Disk resource usage bars.
- **Syntax:**
  ```bash
  ez system-info
  ```
- **Example Output:**
  ```
  ╭─────────────────────────── 💻 System Information ────────────────────────────╮
  │                                                                              │
  │  ── OS & Session ──                                                          │
  │  Distribution            Deepin 25 (crimson) (Debian-based)                  │
  │  Hostname                shaheer-PC                                          │
  │  Kernel                  Linux 6.18.48-amd64-desktop-rolling (x86-64)        │
  │  System Uptime           4 hours, 42 minutes                                 │
  │  Desktop Environment     DDE (Deepin Desktop Environment)                    │
  │  Display Server          X11 - 1366x768                                      │
  │  Shell & Terminal        Bash 5.2.37                                         │
  │  Software Packages       2,161 (dpkg), 3 (flatpak)                           │
  │                                                                              │
  │  ── Hardware Specs ──                                                        │
  │  Computer / Board        Dell Inc. Precision 3520 (BIOS 1.17.1, 01/07/2020)  │
  │  Chassis Type            Laptop 💻                                           │
  │  Processor (CPU)         Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz (8 vCPUs) │
  │  Graphics (GPU)          Intel Kaby Lake-H GT2 [HD Graphics 630] (rev 04)    │
  │  Battery & Power         100% (Full, AC Connected 🔌)                        │
  │                                                                              │
  │  ── Memory & Disk ──                                                         │
  │  Memory (RAM)            5.1 GB / 7.3 GB  ██████░░ 70.0%                     │
  │  Swap Space              1.1 GB / 10.0 GB  █░░░░░░░ 10.9%                    │
  │  Root Storage (/)        8.9 GB / 29.3 GB  ██░░░░░░ 30.2%                    │
  │                                                                              │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ```

---

#### `ez stats`
- **Replaces:** `htop`, `btop`, `top`, `free -h`, `uptime`, `nproc`, `/proc/stat`
- **Why it's better:** Launches a modern, live-updating Textual TUI system metrics and telemetry monitor. Features per-core visual CPU bars, RAM/Swap gauge meters, instant search filtering (`/`), column sorting (`s`), and detailed process inspection (`i`). Seamlessly transitions into `ez task-manager` (`t`) when you want to terminate or manage apps.
- **Interactive Controls:**
  - `t`: Open Task Manager to manage active applications, unresponsive apps, and terminate tasks with auto-elevation.
  - `i` / `Enter`: Detailed process inspection (CWD, open files, binary path, cmdline).
  - `/` or `Ctrl+F`: Search / filter processes in real-time.
  - `s`: Open Sort Picker (Sort by CPU%, Memory%, PID, Resident RAM, or Name).
  - `Space`: Pause / Resume live telemetry updating.
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

#### `ez list [choose-directory]`
- **Replaces:** `ls`, `ls -la`, `tree`, `du -sh *`, `stat <file>`
- **Why it's better:** Modern, flagless, and pathless directory inspection. Form 1 provides an instant, non-interactive pretty listing in your current directory with file emojis, human sizes, and non-blocking background folder sizing. Form 2 visually picks any directory across your filesystem, instantly prints its pretty listing directly to your terminal shell, and provides an optional hotkey (`i`) to open the full interactive TUI inspector (tree view, sort cycles, and stat replacement details modal).
- **Strictly Flagless & Pathless:** Does **not** accept path arguments (`ez list /var` is rejected). Folder selection is always done visually.
- **Syntax:**
  ```bash
  # Form 1: Instant Pretty Listing of Current Directory (Non-Interactive)
  ez list

  # Form 2: Visual Folder Selection + Terminal Listing & Optional TUI Inspector
  ez list choose-directory
  ```
- **Form 2 Features:**
  - **Instant Shell Listing**: Prints the selected directory's Rich table directly to stdout.
  - **Interactive TUI Option (`i`)**: Opens full Textual inspector with:
    - `[t]`: Toggle between flat list table and collapsible tree view.
    - `[s]`: Cycle sorting: Name (A–Z) $\rightarrow$ Size (largest first) $\rightarrow$ Date (newest first).
    - `[h]`: Toggle hidden files and folders.
    - `[Enter]`: Open details modal card with plain English permissions, created/modified dates, exact bytes, and ownership.
    - `[q]` / `[Esc]`: Quit inspector back to shell.


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

#### `ez create-folder [names...] [choose-directory]`
- **Replaces:** `mkdir -p <name>`
- **Why it's better:** Validates naming, detects existing folders, supports creating single or comma-separated multiple folders in current directory, supports visual destination selection, and automatically elevates privileges if creating in a protected system path.
- **Syntax:**
  ```bash
  # Mode 1: Create in Current Directory (Single or Multiple)
  ez create-folder Projects
  ez create-folder folder1, folder2, folder3
  ez create-folder assets/, components/

  # Mode 2: Create in Any Chosen Location Visually
  ez create-folder Projects choose-directory
  ez create-folder dir1, dir2 choose-directory
  ez create-folder choose-directory
  ```

---

#### `ez create-file [names...] [choose-directory]`
- **Replaces:** `touch <name>`
- **Why it's better:** Validates file extensions, prevents accidental overwriting of existing files, supports creating single or comma-separated multiple files in current directory, supports visual destination selection, and automatically elevates privileges if creating in protected directories.
- **Syntax:**
  ```bash
  # Mode 1: Create in Current Directory (Single or Multiple)
  ez create-file script.py
  ez create-file README.md, app.py, styles.css

  # Mode 2: Create in Any Chosen Location Visually
  ez create-file script.py choose-directory
  ez create-file index.html, main.js choose-directory
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

#### `ez package-info [name]`
- **Replaces:** `apt show <name>`, `apt search <name>`, `flatpak search <name>`, `snap find <name>`, `pip show`, `npm list -g`
- **Why it's better:** Follows modern app-store design principles by simultaneously checking your local machine (offline: dpkg/apt, snap, flatpak, pip, npm global, PATH binaries) and remote store catalogs (online: apt repository, Flathub, Snap Store).
  - **Loose Name Resolution**: Prioritizes exact matches, then substring and fuzzy matching across all sources. If multiple candidates match, presents an interactive chooser menu. If nothing is found, provides friendly guidance and closest name suggestions.
  - **Nature Badge**: Automatically identifies and categorizes software into `Desktop App`, `CLI Tool`, `Library`, or `Service`.
  - **Installed Card**: Shows installed status, source badges, version, installed size, summary, and offers safe actions (`Run` via `ez run`, `Uninstall` with dry-run dependency impact preview, and `Details`).
  - **Store Card (Not Installed)**: Shows available provider badges (`[📦 APT Repository]`, `[🟣 Flathub]`, `[🟢 Snap Store]`), latest version, description, and one-click installation via safe elevation.
  - **Offline-First Resilience**: If the internet or stores are unavailable, local findings are immediately displayed alongside a friendly "Store unavailable" notice without crashing.
  - **App Hub Menu (No Argument)**: Running `ez package-info` without arguments opens the EasyCLI Package & App Hub menu with options to inspect installed apps, review pending updates, or search the store.
- **Syntax:**
  ```bash
  ez package-info                  # Opens the App Hub interactive menu
  ez package-info curl             # Inspect installed CLI tool with safe run/uninstall actions
  ez package-info vlc              # Inspect desktop application across local and store sources
  ez package-info requests         # Inspect Python library across pip and APT
  ez package-info cowsay           # Inspect store package and install with safe elevation
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

#### `ez list-installed-packages [apps|packages|both]`
- **Replaces:** `apt list --installed`, `dpkg-query -l`, `flatpak list`, `snap list`, `pip list`, `npm list -g`
- **Why it's better:** Provides an interactive filter so you can view:
  - **[1] 🖥️ Installed Applications Only**: Focus on actual desktop and GUI applications (browsers, media players, editors, etc.) without wading through 2,000 system libraries.
  - **[2] 📦 Packages Only**: System packages, CLI utilities, developer libraries, and runtimes (like npm, node, nala, php, pip, etc.).
  - **[3] 🌟 Both**: Complete inventory of all installed software across APT, Flatpak, Snap, Pip, and global npm.
- **Syntax:**
  ```bash
  ez list-installed-packages           # Interactively asks: Apps, Packages, or Both
  ez list-installed-packages apps      # Directly lists installed applications
  ez list-installed-packages packages  # Directly lists packages & developer libraries
  ez list-installed-packages both      # Lists all installed applications and packages
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

#### Retired: `ez version [name]` (Consolidated into `ez package-info`)
- **Status:** Completely retired.
- **Reason:** `ez package-info` provides a comprehensive App-Store card that includes version detection across binaries on PATH, Debian packages, APT catalog, Snaps, Flatpaks, Python libraries, and Node.js modules alongside size, nature, and safe actions.

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

---

#### `ez compress [targets | choose-directory]`
- **Replaces:** `zip -r <archive.zip> <files...>`, `tar -czf <archive.tar.gz> <files...>`, `tar -cJf <archive.tar.xz> <files...>`, `7z a <archive.7z> <files...>`, `gzip`, `bzip2`
- **Why it's better:** Eliminates cryptic tar/zip flags (`-czvf`, `-cJf`, `-r`, `-9`) and dangerous destination syntax.
  - **Dual-Mode System:**
    - **Direct Mode:** Specify single or multiple files and folders in the current directory (separated by commas or spaces). Subfolder paths are strictly blocked for safety to prevent accidental archives of unexpected locations.
    - **Visual Mode:** Run `ez compress choose-directory` (or `ez compress` with no args) to launch the mini explorer and choose items across any directory.
  - **Interactive TUI Format Selector:** Select between `.zip`, `.tar.gz`, `.tar.xz`, `.7z`, and `.tar.bz2` with clear descriptions of speed vs compression ratio.
  - **Intelligent Default Naming:** Pre-populates the archive name from the selected item name (or `archive.<ext>` for multi-item archives) with easy in-place editing.
  - **Collision Protection:** Checks if the target archive already exists and prompts with `[O]verwrite`, `[R]ename` (e.g. `archive (1).zip`), or `[C]ancel`.
  - **Live Progress & Success Card:** Displays an animated progress bar with current file name, percentage, bytes processed, and time remaining, followed by a summary card showing space saved, file counts, and archive path.
- **Syntax:**
  ```bash
  # Direct mode (current directory items)
  ez compress my_folder/
  ez compress report.pdf notes.txt
  ez compress file1.txt, file2.txt, folder1/

  # Visual picker mode
  ez compress choose-directory
  ez compress
  ```

---

#### `ez extract [archives...] [to <dest> | choose-directory]`
- **Replaces:** `unzip <archive.zip>`, `tar -xvf <archive.tar>`, `tar -xzvf <archive.tar.gz>`, `tar -xJvf <archive.tar.xz>`, `tar -x -C <destination>`, `7z x <archive.7z>`, `unzip <archive.zip> -d <dir>`
- **Why it's better:** Replaces confusing, non-standard unpacking syntax and flags across different archive tools with one intuitive, flagless command:
  - **Direct CWD Extraction:** Running `ez extract <archive>` prompts for destination, defaulting directly to your current working directory upon pressing <kbd>Enter</kbd>.
  - **Targeted Mode (`to <destination>`):** Extract archives directly from your current directory to a specific destination folder. Missing destination folders are created automatically.
  - **Visual Destination Selection (`to choose-directory`):** Select archives directly, then choose the destination folder visually via the mini explorer or interactive prompt.
  - **Two-Stage Visual Mode (`ez extract choose-directory`):** Visual mini explorer launches to pick archive(s) from anywhere on your system, followed by mini explorer to select your target destination folder.
  - **Zip-Slip & Traversal Guard:** Fully sanitizes member paths to block path traversal attacks (`../` or leading `/`).
  - **Automatic Privilege Elevation:** Unpacking to system or root-owned directories triggers seamless, one-time admin elevation.
  - **Universal Format Detection:** Seamlessly extracts `.zip`, `.tar.gz`, `.tgz`, `.tar.xz`, `.txz`, `.tar.bz2`, `.tbz2`, `.tar`, and `.7z`.
  - **Live Progress & Success Card:** Real-time progress bar with active file display, followed by a clean summary card with item counts and destination path.
- **Syntax:**
  ```bash
  # Extract archive (press Enter for current directory, or type 'choose-directory')
  ez extract backup.zip
  ez extract package1.tar.gz, package2.7z, package3.tar.xz

  # Extract archives to a specific destination folder
  ez extract backup.zip to /path/to/destination
  ez extract package1.tar.gz, package2.7z to ./extracted_files/

  # Extract archives with visual destination selection via mini explorer
  ez extract backup.zip to choose-directory

  # Interactive destination prompt (or press Enter for visual destination picker)
  ez extract backup.zip to

  # Visual two-stage extraction across any directory
  ez extract choose-directory
  ez extract
  ```

---

#### `ez run [target | choose-directory] [args...]`
- **Replaces:** `bash script.sh`, `python3 script.py`, `chmod +x && ./bin`, `snap run <app>`, `flatpak run <id>`, `gio launch <desktop>`, `./app.AppImage`
- **Why it's better:** Eliminates the confusion of having multiple incompatible ways to run scripts and applications on Linux:
  - **Universal Target Resolution Hierarchy:**
    1. *Local File:* Checks if the target exists in the current directory or filesystem. If it's a binary, runs it. If it's a script without executable permissions, prompts to `chmod +x` with consent or falls back to its detected interpreter (`python3`, `bash`, `node`, `ruby`, `perl`, `php`). If it's an AppImage, verifies permissions and catches missing FUSE libraries (`libfuse2`) with helpful installation guidance.
    2. *Application Name:* Checks PATH binary, Snap application, Flatpak application, and desktop entries (`/usr/share/applications/`, `~/.local/share/applications/`).
  - **GUI vs CLI Intelligence:**
    - *GUI Applications:* Detected via desktop entry (`Terminal=false`), AppImage, or graphical Snap/Flatpak. Launches **detached in the background** (`subprocess.Popen(..., start_new_session=True)`). Your terminal stays immediately free, displaying a confirmation banner and a reminder pointing to `ez task-manager`.
    - *CLI Tools:* Executed directly in the foreground, with a mandatory `▶ Running: <cmd>` summary line printed before execution.
  - **Flag-Free Guided Mode:**
    - When a CLI target is run without arguments, EasyCLI automatically discovers available options.
    - *Static AST/Regex Inspection:* Analyzes Python scripts (AST `add_argument`) and Shell scripts (`getopts`, `case`) statically without executing them to prevent unwanted side-effects.
    - *Safe Dynamic Help Probing:* Probes `--help` with `stdin=/dev/null` and timeout. Only probes `-h` if `--help` output specifically referenced it and contained standard help markers. Never triggers flags that do real work.
    - *Interactive Form:* Questions are presented in sequence. Press **Enter** to skip any option and keep defaults. Select paths directly or pick them visually with `choose-directory`.
    - *Mandatory Preview & Confirmation:* Displays the assembled command in a high-contrast preview panel and prompts for confirmation before running. Never skipped.
  - **Ambiguous Flatpak Selection:** When a name matches multiple Flatpak packages (e.g. `firefox` matching stable and developer editions), displays an interactive numbered selection table.
  - **Usage Error Fallback:** If a CLI tool run without arguments exits with an error code, offers to launch Guided Mode to configure required flags.
  - **Automatic Privilege Elevation:** Prompts for administrator elevation if execution fails with permission errors (`PermissionError`, code 126/13).
- **Syntax:**
  ```bash
  # Run local scripts, binaries, or AppImages directly
  ez run script.py
  ez run script.sh
  ez run my_binary
  ez run Cursor.AppImage

  # Launch installed applications from any source
  ez run vlc
  ez run spotify
  ez run gimp

  # Pass arguments directly (skips guided mode)
  ez run script.py --input data.csv --output out.csv
  ez run curl -s https://example.com

  # Pick an executable or script visually via mini explorer
  ez run choose-directory
  ```


