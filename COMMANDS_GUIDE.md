# 📖 EasyCLI (`ez`) Complete Commands Guide & Linux Command Replacement Map

EasyCLI (`ez`) provides beginner-friendly, visually rich, and interactive modern alternatives to traditional Linux terminal commands. Instead of memorizing obscure flags, cryptic syntax, or risk-prone bash utilities, EasyCLI presents clean colored cards, live visual monitors, interactive file managers, and reversible safety mechanisms.

---

## 🗺️ Quick Command Replacement Matrix

| EasyCLI Command | Traditional Linux Command(s) Replaced | Primary Pain Points Solved |
| :--- | :--- | :--- |
| `ez system-info` | `hostnamectl`, `uptime -p`, `/etc/os-release`, `uname -r` | No need to run 4 separate commands and parse raw unformatted text. |
| `ez stats` | `htop`, `top`, `free -h`, `uptime`, `nproc`, `ps aux`, `kill` | Live Textual process monitor with per-core CPU bars, search filter, and safe GUI-style kill confirmation. |
| `ez disk-info` | `df -h` | Eliminates screen-cluttering pseudo-filesystems (snap, loop, tmpfs, udev); adds visual colored usage bars. |
| `ez big-files [dir]` | `du -h --max-depth=1 \| sort -hr \| head -n 10` | Eliminates long piped pipelines; displays live spinner and formatted table with path picker. |
| `ez logs [N]` | `journalctl -n N --no-pager`, `dmesg` | Color-codes error logs in red, warnings in yellow, and ok logs in green with severity filters. |
| `ez choose-directory` | `ranger`, `mc`, `cd`, `ls -la`, `xdg-open` | Full graphical terminal file manager with mouse support, file emojis, bookmarks, and subshell launcher. |
| `ez copy [file/folder]` | `cp -r <src> <dest>` | Adds desktop-style 2-stage clipboard (`ez copy` then `ez paste`) with collision detection and undo support. |
| `ez move [file/folder]` | `mv <src> <dest>` | Reversible cut-and-paste with conflict resolution and automated rollback. |
| `ez paste [dir]` | *(No direct equivalent — GUI desktop clipboard)* | Pastes staged files/folders directly or visually with overwrite confirmation and collision auto-rename. |
| `ez undo` | *(No native bash equivalent — lost data)* | One-click rollback for the last paste operation (restores overwritten files and reverses moves). |
| `ez redo` | *(No native bash equivalent)* | Re-applies the most recently undone operation with safety verification. |
| `ez create-folder [name]` | `mkdir -p <name>` | Validates folder names, detects existing folders, and allows picking target directory visually. |
| `ez create-file [name]` | `touch <name>` | Validates extensions, prevents accidental overwrites, and supports visual destination selection. |
| `ez delete [target]` | `rm -rf <target>`, `rmdir` | Prevents catastrophic mistakes: non-force check first, explicit item summary, and safe auto-elevation. |
| `ez edit-file [target]` | `nano`, `vim`, `micro`, `sudoedit` | Modern code & text editor with syntax highlighting, find & replace, mouse support, and elevated saving. |
| `ez package-search <kw>` | `apt search`, `flatpak search`, `snap find` | Unified universal search across **APT 📦**, **Flatpak 🟣**, and **Snap 🟢** with one-click install commands. |
| `ez package <name>` | `apt show <name>`, `dpkg -s <name>` | Human-readable package card showing version, size, description, and installed status without wall of text. |
| `ez available-updates` | `apt list --upgradable` | Clean summary table of available upgrades without modifying system lists or running unexpected updates. |
| `ez installed-packages` | `apt list --installed`, `dpkg-query -l`, `flatpak list` | Comprehensive list of installed software across system packages and desktop applications. |
| `ez installed-package-search` | `apt list --installed \| grep -i <kw>` | Case-insensitive search through installed system software without complex bash regex. |
| `ez service-status <name>` | `systemctl status <name>`, `is-active`, `is-enabled` | Clean service card with green/red status badges and boot startup state. |
| `ez network-info` | `ip -br addr`, `ip route`, `/etc/resolv.conf`, `ping` | Single overview card showing IP, interfaces, gateway, DNS servers, and Internet connectivity. |
| `ez` *(no args)* | *(Manual CLI navigation)* | Full interactive TUI menu with searchable features, descriptions, and action navigation. |
| `ez help` | `man`, `--help` | Formatted table of commands, arguments, examples, and safety guidelines. |

---

## 🛠️ Detailed Command Reference

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

#### `ez big-files [folder]`
- **Replaces:** `du -h --max-depth=1 <folder> | sort -hr | head -n 10`
- **Why it's better:** Replaces a long, error-prone shell pipe with a single command. Includes an animated scanner spinner and supports visual folder picking via `choose-directory`.
- **Syntax:**
  ```bash
  ez big-files                  # Scans home directory (~)
  ez big-files /var/log         # Scans specific folder
  ez big-files choose-directory # Picks directory visually
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
- **Replaces:** `ranger`, `mc`, `cd`, `ls -la`
- **Why it's better:** A full graphical terminal file manager built with Textual. Includes full mouse support, single-character file type emojis, bookmarks (Home, Documents, Downloads, Desktop), file details, hidden files toggle (`.`), and a subshell launcher (`o`) that drops you directly into any folder.
- **Syntax:**
  ```bash
  ez choose-directory           # Opens in current folder
  ez choose-directory ~         # Opens in Home directory
  ez choose-directory /var/log  # Opens in specific folder
  ```

---

#### `ez copy [target]` & `ez move [target]`
- **Replaces:** `cp -r <src> <dest>` and `mv <src> <dest>`
- **Why it's better:** Implements desktop-style clipboard staging. You stage files or folders directly in the terminal without specifying the destination yet.
- **Syntax:**
  ```bash
  # Copy or move items in current directory:
  ez copy document.txt
  ez copy my_folder/
  ez move report.pdf

  # Or pick items visually from anywhere:
  ez copy choose-directory
  ez move choose-directory
  ```

---

#### `ez paste [destination]`
- **Replaces:** GUI desktop clipboard paste
- **Why it's better:** Pastes staged files/folders with safety pre-checks:
  1. Shows itemized summary of what will be copied or moved.
  2. Automatic collision detection (Option to Skip, Overwrite, or Auto-Rename).
  3. Safe permission elevation if pasting into a write-protected directory (e.g. `/etc` or `/var`).
  4. Automatic undo log registration so changes can be reverted instantly.
- **Syntax:**
  ```bash
  ez paste                  # Pastes directly into current directory
  ez paste choose-directory # Selects destination folder visually
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

#### `ez create-folder [name]` & `ez create-file [name]`
*(Aliases: `ez new-folder`, `ez new-file`)*
- **Replaces:** `mkdir -p <name>` and `touch <name>`
- **Why it's better:** Validates naming, prevents accidental overwriting of existing files, and allows visual destination selection.
- **Syntax:**
  ```bash
  ez create-folder Projects
  ez create-folder choose-directory

  ez create-file script.py
  ez create-file choose-directory
  ```

---

#### `ez delete [target]`
*(Aliases: `ez del`, `ez remove`)*
- **Replaces:** `rm -rf <target>`, `rmdir <target>`
- **Why it's better:** Traditional `rm -rf` has caused countless catastrophic data losses. `ez delete`:
  1. Non-force first: Warns if folder is non-empty before proceeding.
  2. Displays confirmation card showing exact items and total size.
  3. Prompts for explicit user confirmation (`[y/N]`).
  4. Safe auto-elevation if deleting protected root files.
- **Syntax:**
  ```bash
  ez delete file.txt
  ez delete old_folder/
  ez delete choose-directory
  ```

---

#### `ez edit-file [target]`
- **Replaces:** `nano`, `vim`, `micro`, `gedit`, `sudoedit`
- **Why it's better:** A full modern terminal text & code editor with syntax highlighting for 15+ languages (Python, JS/TS, Bash, Markdown, HTML, CSS, Rust, Go, SQL, JSON, YAML). Includes mouse support, visual Find & Replace (`Ctrl+F`), line jumping (`Ctrl+G`), soft word wrap (`Ctrl+W`), and automated elevation when editing protected configuration files (like `/etc/hosts` or `/etc/fstab`).
- **Syntax:**
  ```bash
  ez edit-file config.yaml
  ez edit-file /etc/hosts
  ez edit-file choose-directory
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

#### `ez installed-packages` & `ez installed-package-search <name>`
*(Alias: `ez installed`)*
- **Replaces:** `apt list --installed`, `dpkg-query -l`, `flatpak list`, `snap list`
- **Why it's better:** Lists all installed system software across APT and desktop sandboxes without truncating names or requiring complex piping to `grep`.
- **Syntax:**
  ```bash
  ez installed-packages
  ez installed-package-search python
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

### 5. Interactive Navigation & Assistance

#### `ez` *(No Arguments)*
- **Replaces:** Manual command memorization
- **Why it's better:** Launches the EasyCLI interactive terminal menu with categories, emoji icons, command descriptions, and keyboard shortcuts (`[b]` Back, `[r]` Refresh, `[q]` Quit).

#### `ez help`
- **Replaces:** `man <tool>`, `--help`
- **Why it's better:** Outputs a clean, categorized table of all subcommands, arguments, and practical examples.
