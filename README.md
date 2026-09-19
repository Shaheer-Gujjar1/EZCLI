# EasyCLI (`ez`) v0.5

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

## 🗑️ Uninstallation

To completely uninstall EasyCLI from your system:

### Option 1: Automated Uninstaller (Recommended)
Run the uninstaller script from the repository:
```bash
cd /path/to/EZCLI
./uninstall.sh
```
This interactively prompts and safely removes:
- The command symlink (`/usr/local/bin/ez`)
- User data, bookmarks, undo history, and local virtualenv (`~/.local/share/ez/`)
- Optional emoji font priority override (`~/.config/fontconfig/conf.d/99-noto-color-emoji.conf`)

### Option 2: Manual Removal
Run the following commands:
```bash
# 1. Remove the binary symlink
sudo rm -f /usr/local/bin/ez /usr/local/bin/ezcli

# 2. Remove user data, bookmarks, and local virtualenv
rm -rf ~/.local/share/ez ~/.local/share/ezcli

# 3. (Optional) Remove font priority override if applied
rm -f ~/.config/fontconfig/conf.d/99-noto-color-emoji.conf
fc-cache -fv ~/.config/fontconfig/conf.d
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

> 💡 **Looking for a comprehensive comparison?** See the full [EasyCLI Commands Guide & Linux Replacement Matrix](COMMANDS_GUIDE.md) for in-depth command breakdowns, interactive hotkeys, and traditional Linux command mappings.

| Icon | Full Command & Syntax | Version | Wrapped Tools | Description |
| :---: | :--- | :---: | :--- | :--- |
| 💻 | `ez system-info` | **v0.1** | `hostnamectl`, `uptime -p`, `/etc/os-release` | Key-value card with OS name/version, hostname, kernel, architecture, and uptime. |
| ⚡ | `ez stats` | **v0.3** | `/proc`, `free`, `uptime`, `nproc` | Live-updating system metrics monitor (modern `btop`/`htop` alternative with per-core CPU bars, RAM/Swap gauges, and top resource consumers). |
| 📋 | `ez task-manager` | **v0.4** | *(Windows Task Manager)*, `ps`, `kill` | Lite & modern Windows-style task manager for user apps with mouse support, emoji icons, unresponsive detection, and instant termination. |
| 🔒 | `ez task-manager-pro` | **v0.4** | `ps aux`, `top`, `sudo kill` | Comprehensive pro task manager with user apps, background daemons, system services, category tabs, and auto admin elevation. |
| 💽 | `ez disk-info` | **v0.1** | `df -h` | Table of storage mounts, sizes, used/available space, and inline usage bars (filters out pseudo-filesystems). |
| 📁 | `ez big-files [path \| choose-directory]` | **v0.1** | `du -h --max-depth=1`, `find` | Table of largest files and folders. Provide a path or use `choose-directory` to pick visually via the mini explorer. Defaults to `~`. |
| 📦 | `ez package-info [name]` | **v0.5** | `apt show`, `apt search`, `flatpak`, `snap`, `pip`, `npm` | App-Store package inspector: checks local machine & stores simultaneously, loose matching, nature classification, and safe actions (Run/Install/Uninstall). Hub menu if no arg. |
| 🔄 | `ez available-updates` | **v0.1** | `apt list --upgradable` | Table of upgradable packages and versions using existing lists only (never runs `apt update`). |
| 🔄 | `ez update` | **v0.4** | `apt update`, `apt-get update` | Refresh package catalog from repositories without installing or modifying software. Safe elevation. |
| 🚀 | `ez upgrade` | **v0.4** | `apt upgrade`, `snap refresh`, `flatpak update` | Comprehensive upgrade across APT, Flatpak, and Snap with impact simulation, Timeshift restore point prompt, and reboot check. |
| 🧹 | `ez uninstall <name>` | **v0.4** | `apt remove`, `snap remove`, `flatpak uninstall` | Safe application uninstallation across APT, Flatpak, and Snap with warning card, single consent, and zero-cache admin elevation. |
| 🔧 | `ez service-status <name>` | **v0.1** | `systemctl is-active`, `systemctl is-enabled` | Status card with running state and boot enablement indicators. |
| 🌐 | `ez network-info` | **v0.1** | `ip addr`, `ip route`, `/etc/resolv.conf` | Overview card and table of network interfaces, IP addresses, gateway, DNS, and online status. |
| 📄 | `ez logs [N]` | **v0.1** | `journalctl -n N --no-pager` | Color-coded system logs by severity (errors red, warnings yellow, ok green). Defaults to 50 lines. |
| 📋 | `ez list-installed-packages [apps\|packages\|both]` | **v0.5** | `apt list --installed`, `dpkg-query`, `flatpak`, `snap`, `pip`, `npm` | List installed software with interactive filter (Installed Applications Only, Packages Only like npm/node/nala/php/pip, or Both). |
| 🗂️ | `ez list [choose-directory]` | **v0.6** | `ls`, `tree`, `du`, `stat` | Modern visual listing & inspector: instant emoji listing of current dir with streaming background folder sizing (Form 1), or visual picker + interactive TUI with flat/tree views, sorting, hidden toggle, and plain English permissions card (Form 2). Strictly no path arguments. |
| 🔎 | `ez installed-package-search <name>` | **v0.1** | `apt list --installed \| grep -i <name>`, `dpkg-query` | Search installed packages and applications by name (wraps `apt list --installed \| grep -i <name>`). |

| 📁 | `ez choose-directory [path]` | **v0.2** | `explorer` | Graphical terminal file explorer with mouse navigation, file-type emojis, bookmarks, and subshell launcher. |
| 📋 | `ez copy [target \| choose-directory]` | **v0.2** | `cp` | Copy file/folder in current directory directly or choose visually with `choose-directory`. |
| 🚚 | `ez move [target \| choose-directory]` | **v0.2** | `mv` | Move file/folder in current directory directly or choose visually with `choose-directory`. |
| 📥 | `ez paste [choose-directory]` | **v0.2** | `paste` | Paste staged items into current directory, or choose destination with `choose-directory`. |
| ⏪ | `ez undo` | **v0.2** | `undo` | Revert the most recent paste operation with preview and confirmation. |
| ⏩ | `ez redo` | **v0.2** | `redo` | Re-apply the most recently undone operation with preview and confirmation. |
| 📁 | `ez create-folder <names...> [choose-directory]` | **v0.3** | `create-folder` | Create one or more new folders directly (comma-separated, in current directory) or choose parent directory visually with mini explorer. Automatic privilege elevation. |
| 📄 | `ez create-file <names...> [choose-directory]` | **v0.3** | `create-file` | Create one or more new blank files directly (comma-separated, in current directory) or choose destination directory visually with mini explorer. Automatic privilege elevation. |
| 🧹 | `ez delete [target \| choose-directory]` | **v0.3** | `delete` | Permanently delete file(s) or folder(s) with explicit consent, non-force-first safety, and automatic elevation. |
| 📝 | `ez edit-file [target \| choose-directory]` | **v0.3** | `edit-file` | Modern terminal text and code editor with syntax highlighting, line numbers, visual search, and auto-elevation. |
| 📶 | `ez check-internet` | **v0.5** | `ping`, `ip route`, `socket` | 3-stage visual connectivity pipeline (`Router → DNS → Internet`) with latency (`✔`/`✖`) and an immediate "Why internet isn't working" one-line diagnostic verdict. |
| 📶 | `ez connect-wifi` | **v0.5** | `nmcli`, `iw` | In-terminal graphical Wi-Fi manager with mouse support, signal strength bars, network scanning, password entry modal with show/hide toggle (`👁️`/`🙈`), and action buttons (`Connect`, `Cancel`, `Refresh`, `Disconnect`). |
| 🔍 | `ez search-file <term>` | **v0.5** | `find`, `locate`, `ls` | Fast fuzzy file search starting from `/home`, rich results table with emoji icons, interactive selection to open, copy path, or edit, and optional system-wide (`'/'`) fallback with auto-elevation. |
| 📦 | `ez compress [targets \| choose-directory]` | **v0.5** | `zip`, `tar`, `gzip`, `xz`, `7z` | Compress files and folders into `.zip`, `.tar.gz`, `.tar.xz`, `.7z`, or `.tar.bz2` with interactive TUI format selector, comma-separated targeting, `choose-directory` mini explorer, and live progress. |
| 📂 | `ez extract [archives...] [to <dest> \| choose-directory]` | **v0.5** | `unzip`, `tar`, `7z` | Extract archive(s) into current directory, specific destination (`to <path>`), visual picker (`to choose-directory`), or launch two-stage mini explorer. Auto-elevation for protected paths. |
| 🕒 | `ez time-machine [list \| create [comment]]` | **v0.6** | `rsync`, `cp`, `btrfs` | Standalone mini Timeshift system restore point manager: visual timeline TUI with rsync hardlink deduplication, create restore point modal (`c`), safe rollback with pre-flight simulation (`r`), delete (`d`), and visual snapshot browsing (`b`). Zero external dependencies. |
| 🧹 | `ez cleanup` | **v0.6** | `apt-get clean`, `apt-get autoremove`, `rm` | Safe system cleaner: scans APT cache, orphan packages with desktop-critical protection, trash, old logs, and thumbnails. Interactive category selection, simulation preview, and freed space summary. |
| 👤 | `ez profile` | **v0.6** | `whoami`, `id`, `chpasswd` | User information card (username, GECOS, groups, sudo rights, home, shell) and change password TUI modal with dot feedback, show/hide toggle, arbitrary length support, and secure stdin chpasswd. |
| 🔧 | `ez fix-packages` | **v0.6** | `dpkg --configure -a`, `apt-get --fix-broken install` | Automated broken package repair: detects interrupted installations and missing dependencies, displays simulation preview and risk badge, with elevated repair execution and all-clear status card. |
| 🚀 | `ez startup-apps [name]` | **v0.6** | `systemctl enable/disable`, `autostart` | Manage login applications and boot services: interactive TUI with two tabs (Login Apps & Boot Services), non-root desktop overrides, elevated systemd toggles, preview lines, and typed confirmation for critical services. Direct mode supported. |


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

### 1. Create Folders Directly (Single or Multiple)
```bash
# Single folder:
ez create-folder my_project

# Multiple folders in current directory (comma-separated):
ez create-folder folder1, folder2, folder3
ez create-folder assets/, components/, styles/
```
Creates new directories in your current location with an immediate summary card.

### 2. Choose Where to Create Visually
```bash
ez create-folder my_project choose-directory
ez create-folder dir1, dir2 choose-directory
# Or simply launch picker:
ez create-folder choose-directory
```
Opens the mini file explorer so you can navigate and pick your desired parent directory visually.

### 3. Create Blank Files (Single or Multiple)
```bash
# Single file:
ez create-file notes.txt

# Multiple files in current directory (comma-separated):
ez create-file README.md, app.py, styles.css

# Or choose directory visually:
ez create-file notes.txt choose-directory
ez create-file index.html, main.js choose-directory
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

## 🔄 Software Catalog Updates & System Upgrade (v0.4)

EasyCLI v0.4 introduces two dedicated, privileged package management commands that streamline software maintenance with beginner-friendly guardrails:

### 1. `ez update` — Software Catalog Refresh (Read-Only)
Refreshes the local repository index (`apt-get update`) with elevated rights, without modifying or installing any packages on your machine:
```bash
ez update
```
- **Consent Flow**: Displays an explanation card highlighting that this is strictly a read-only metadata refresh, requests consent, and prompts for your admin password with dots (`●●●●`).
- **Informational Summary**: Displays how many upgradable packages are now known and counts of updated vs. cached repositories.
- **Fault-Tolerant**: Captures individual PPA and repository warnings (e.g. expired GPG keys or skipped architectures) without crashing.
- **Reassuring Reminder**: Concludes with: *"This was only an information refresh — nothing was installed. You do not need to run this repeatedly."*

### 2. `ez upgrade` — Comprehensive Multi-Source System Upgrade
Orchestrates a comprehensive, non-destructive upgrade across **APT**, **Flatpak**, and **Snap** under a single elevation consent:
```bash
ez upgrade
```
- **Step 1 — Refresh**: Refreshes package lists across all available packaging ecosystems.
- **Step 2 — Impact Simulation Preview**:
  - Displays package counts, estimated download size, and disk space delta.
  - Highlights any held-back packages with an explanation that they are preserved for system stability.
  - Assigns an intelligent **Risk Badge** (`Medium Risk` for standard updates, `High Risk` if updating the Linux kernel, systemd, or libc6).
  - Recommends creating a **Timeshift restore point** snapshot if Timeshift is installed.
- **Step 3 — Explicit Confirmation**: Prompts for confirmation (`[y/N]`) before any changes are made.
- **Step 4 — Per-Source Execution**: Runs standard non-destructive upgrades (`apt-get upgrade`, `flatpak update`, `snap refresh`) sequentially with progress indicators.
- **Step 5 — Summary & Reboot Check**: Checks `/var/run/reboot-required` and reminds the user if core components require a restart. Concludes with: *"Done. Run this only when you choose to — there is no daily obligation."*

### 3. `ez uninstall <name>` — Safe Multi-Source Application Removal
Safely uninstalls software across **APT**, **Flatpak**, and **Snap** with clear impact warnings and zero-cache admin elevation:
```bash
ez uninstall vlc
```
- **Automatic Multi-Source Resolution**: Automatically checks if the application is installed via APT, Flatpak, or Snap. If multiple installations exist, provides an interactive menu to choose which instance to remove.
- **Pre-Removal Warning Card**: Displays a formatted card with the application name, package ID, platform badge, installed version, space occupied, and impact notices.
- **Single Consent & Non-Cached Authentication**: Requires a single explicit confirmation (`[y/N]`) and prompts for the admin password with dots (`●●●●`). Strictly **never caches or persists your admin password** in memory or on disk.
- **Reassuring Summary**: Shows an uninstallation completion panel confirming removal of application binaries and desktop integrations.

### 4. `ez task-manager` & `ez task-manager-pro` — Lite & Modern Terminal Task Manager
Windows-inspired, ultra-light terminal Task Manager featuring full mouse support, emoji icons, real-time gauges, and unresponsive process detection:
```bash
ez task-manager       # Normal Mode: Interactive User Applications only
ez task-manager-pro   # Pro Mode: All tasks (Apps + Background Daemons + System Services)
```
- **Normal Mode (`ez task-manager`)**: Displays only your running user applications (browsers, IDEs, media players, terminals). Automatically hides noisy system daemons, systemd units, and kernel threads.
- **Pro Mode (`ez task-manager-pro`)**: Comprehensive administrator view with all active processes classified into category tabs (`[All]`, `[Apps]`, `[Background]`, `[System]`, `[Unresponsive]`).
- **Unresponsive Detection**: Detects hung processes in uninterruptible sleep (`D`), zombie state (`Z`), or stopped state (`T`), prominently highlighting them with `⚠️ Unresponsive` badges.
- **Mouse & Keyboard Controls**: Click rows to select, double-click or press `Del`/`k` to End Task, click column headers to sort by CPU %, Memory %, Name, PID, or Status, press `/` to live filter.
- **Automatic Elevation**: In Pro Mode, terminating root or system processes automatically elevates through the privileged helper without needing to launch EasyCLI as root.

### 5. `ez package-info [name]` — Universal Package & Version Inspector
A unified, App-Store styled inspector that consolidates software inspection, store catalogs, and version checking into one command:
```bash
ez package-info curl    # Context-aware card with installed status, versions, nature, and actions
ez package-info         # Interactive search hub across APT, Flathub, Snap, Pip, and PATH
```
- **Unified Multi-Source Detection**: Inspects binaries on PATH, Debian packages (`dpkg`/`apt`), Flathub/Flatpak, Snap Store, Python (`pip`), and Node.js (`npm`), reporting installed version, store version, install size, and desktop launcher nature.
- **Safe Actions**: Run, Install, or Uninstall directly from the card.
- **Unified Version & Package Inspection**: Standalone `ez version` is completely retired; all version checking and package inspection is handled by `ez package-info <name>`.

### 6. `ez check-internet` — Universal Internet Connectivity Checker (v0.5)
Instant 3-stage connectivity diagnosis and visual pipeline:
```bash
ez check-internet
```
- **3-Stage Visual Pipeline**:
  - **Local Router**: Resolves default gateway from `ip route` and measures ICMP ping latency.
  - **DNS Resolution**: Checks nameservers in `/etc/resolv.conf` and times live hostname lookup (`google.com`, `cloudflare.com`).
  - **Internet Reachability**: Tests end-to-end access to public anycast endpoints (`1.1.1.1`, `8.8.8.8`) using ICMP ping with transparent TCP socket fallback (port 53/443) if ICMP is filtered.
- **Visual Display**: Renders a high-contrast pipeline (`Router ✔ (1.6 ms) ➔ DNS ✔ (24.3 ms) ➔ Internet ✔ (26.2 ms)`), an itemized diagnostics table, and a dedicated verdict panel.
- **"Why internet isn't working" One-Line Reply**: Pinpoints whether the issue is local Wi-Fi/cable disconnect, router timeout, DNS failure, ISP outage, or a restrictive firewall.

### 7. `ez connect-wifi` — In-Terminal Graphical Wi-Fi Manager (v0.5)
Interactive terminal Wi-Fi application featuring full mouse support, real-time signal bars, and password entry:
```bash
ez connect-wifi
```
- **Full Mouse & Keyboard Navigation**: Click any network row to select, double-click to connect, or use keyboard shortcuts (`[c]` Connect, `[r]` Refresh, `[d]` Disconnect, `[q]` Close).
- **Network Scanner**: Automatically discovers nearby Wi-Fi networks, displays signal bars (`▂▄▆█ 85% 📶`), detects security encryption (`🔒 WPA2/WPA3` / `🔓 Open`), and highlights your active connection (`🟢 Connected`).
- **Password Modal with Visibility Toggle**:
  - Secure masked password field by default (`••••••••`).
  - Click `👁️ Show Password` to reveal plaintext and avoid typos, toggling back to `🙈 Hide Password`.
  - Action buttons: `[🔗 Connect]` and `[❌ Cancel]`.
- **Action Toolbar**: Clickable buttons for `🔗 Connect`, `🔄 Refresh`, `🚫 Disconnect`, and `❌ Close`.
- **Search & Filter**: Press `[/]` to search and filter SSIDs in real time.

### 8. `ez search-file` — Fuzzy File Search & Interactive Actions (v0.5)
Fast fuzzy file finder with `/home`-first sequencing, system-wide `'/'` fallback with administrator rights, and interactive action choices:
```bash
ez search-file <term>
```
- **Sequenced Search Scope**: Searches `/home` first to deliver instant, relevant results.
- **"Didn't Find It?" System-Wide Option**:
  - If 0 matches are found in `/home`, automatically prompts: *"File not found in /home. Wanna look in whole system? '/' [y/N]"*.
  - Even if matches are found in `/home`, a prominent option (`[s] 🌐 Search entire system ('/')`) is provided so users can expand the search if their desired file was elsewhere.
- **Safe Auto-Elevation**: Scans protected system directories (`/etc`, `/var`, `/root`, `/opt`) using EasyCLI's safe privilege elevation while safely pruning pseudo-filesystems (`/proc`, `/sys`, `/dev`).
- **Interactive Action Menu**:
  - `[1] 📂 Open`: Launches the selected file in your system's default graphical application (`xdg-open`).
  - `[2] 📋 Copy path`: Copies the absolute path directly to your clipboard (via OSC 52 and `wl-copy`/`xclip`/`xsel`) and displays it prominently.
  - `[3] ✏️ Edit`: Launches the file in EasyCLI's integrated code and text editor.
  - `[q] ❌ Quit`: Clean exit.

### 9. `ez compress` — Multi-Format Archive Compression & Live Progress (v0.5)
Compress files or directories into modern archive formats (`.zip`, `.tar.gz`, `.tar.xz`, `.7z`, `.tar.bz2`) with interactive format selection, live byte-accurate progress, and detailed success metrics:
```bash
# Direct mode in current directory (single, multiple, or comma-separated)
ez compress folder1/ folder2/
ez compress file1.txt, file2.txt, folder1/

# Visual multi-selection mode across any directory
ez compress choose-directory
```
- **Current Directory Scope**: Direct arguments are restricted to items in your current directory for safety. Accidental subfolder targeting is blocked, directing users to `choose-directory`.
- **Comma & Space Separation**: Supports space-separated, comma-separated (`a.txt, b.txt`), and mixed argument lists across all direct file operations.
- **Interactive TUI Format Selector**: Choose from `.zip`, `.tar.gz`, `.tar.xz`, `.7z`, or `.tar.bz2` with live item counts, estimated size, and auto-populated archive naming.
- **Conflict Guard**: Prompts to `[O]verwrite`, `[R]ename`, or `[C]ancel` if an archive already exists.
- **Live Progress System**: Real-time progress bar showing active file being packed, percent complete, bytes compressed, and remaining time.
- **Success Summary Card**: Displays archive location, compression ratio, space saved, and elapsed execution time.

### 10. `ez extract` — Safe Multi-Format Archive Extraction (v0.5)
Extract any modern archive format (`.zip`, `.tar.gz`, `.tar.xz`, `.7z`, `.tar.bz2`, `.tar`, `.tgz`, `.txz`, `.tbz2`) without remembering cryptic command-line flags:
```bash
# Extract archives (prompts: press Enter for current directory, or type 'choose-directory')
ez extract backup.zip
ez extract package1.tar.gz, package2.7z, package3.tar.xz

# Extract archives to a specific destination folder
ez extract backup.zip to /path/to/destination
ez extract package1.tar.gz, package2.7z to ./extracted_files/

# Extract archive with visual destination selection via mini explorer
ez extract backup.zip to choose-directory

# Interactive destination prompt (or press Enter for visual destination picker)
ez extract backup.zip to

# Full two-stage visual extractor: pick archive(s) then pick destination folder
ez extract choose-directory
```
- **Unified Extraction**: Directly extract in your current working directory (press <kbd>Enter</kbd>), specify a destination path (`to <folder>`), or choose visually (`choose-directory`).
- **`ez extract ... to <destination>` (Targeted Mode)**: Extract one or multiple archives in the current directory to any destination folder on your system. Automatically creates non-existent destination directories.
- **`to choose-directory` & Interactive `to`**: Allows selecting source archives directly from the current directory, while opening the mini explorer to pick the destination directory visually.
- **Two-Stage Visual Explorer (`ez extract choose-directory`)**: Mini explorer opens first to choose archive(s), then opens again to select the destination directory.
- **Auto-Elevation for Protected Destinations**: Extracting to root-protected directories (e.g. `/opt`, `/etc`) prompts for standard single elevation consent and unpacks safely via staging and the privileged helper.
- **Zip-Slip & Path Traversal Protection**: Every archive entry is thoroughly sanitized against path traversal vulnerabilities (e.g. `../../etc/passwd` or absolute root paths).
- **Live Progress & Success Summary**: Real-time progress bar tracking extracted files, byte volume, and percent, followed by a clean extraction summary card.

### 11. `ez run` — Universal Runner & Flag-Free Guided Mode (v0.5)
One single universal command to execute any file (script, binary, AppImage) or launch installed applications from any source (**PATH binaries**, **Snap**, **Flatpak**, or **Desktop entries**), with an interactive flag-free Guided Mode for beginners:
```bash
# Run local scripts or binaries directly
ez run script.py
ez run ./build/my_app
ez run application.AppImage

# Launch applications from any system source
ez run vlc
ez run spotify
ez run gimp

# Pass through flags and arguments directly (skips guided mode)
ez run script.py --input data.csv --verbose
ez run curl https://example.com -o page.html

# Interactive visual file picker via mini explorer
ez run choose-directory
```
- **Strict Resolution Hierarchy**:
  1. *Local file path*: Executable binaries run directly; non-executable scripts run via detected interpreter (`.py` via `python3`, `.sh` via `bash`, `.js` via `node`) with consent to `chmod +x`; AppImages run with permissions check and FUSE guidance.
  2. *Application name*: Resolves via PATH binary, Snap (`snap run`), Flatpak (`flatpak run`), or desktop entry (`gio launch`).
- **GUI vs CLI Intelligence**:
  - *GUI applications* (desktop entries with `Terminal=false`, AppImages, graphical Snaps/Flatpaks) launch **detached in the background**. The terminal stays immediately free with a confirmation card and a helpful tip pointing to `ez task-manager`.
  - *CLI tools* execute in the foreground with a mandatory `▶ Running ...` summary line displayed before execution.
- **Flag-Free Guided Mode**:
  - When a CLI tool is invoked without arguments (`ez run <target>`), EasyCLI discovers configurable options safely.
  - *Static script analysis first*: Parses Python `argparse` AST or Shell `getopts`/`case` branches without executing the script to avoid side-effects.
  - *Safe dynamic help probe*: Probes `--help` safely (`stdin=/dev/null`, timeout=2.5s). Only probes `-h` if `--help` specifically suggested it and output contains standard help markers.
  - *Interactive question form*: Prompts for boolean flags, choice selections, and paths (with visual mini explorer option picker). Users can press **Enter** to skip and keep defaults.
  - *Mandatory Preview & Confirmation*: Always displays the assembled command in a high-contrast preview card and prompts for explicit user confirmation before running.
- **Ambiguous Flatpak Selection**: If multiple Flatpak applications match a name (e.g. `firefox` matching stable and developer editions), an interactive Rich selection table is presented to choose the intended package.
- **Automatic Privilege Elevation**: Commands or files failing due to `Permission denied` (EACCES / exit code 126 or 13) seamlessly prompt for elevation and run via the privileged helper with dot password feedback.
- **Missing App Guidance**: If an application is not installed, displays a clean card suggesting: `ez package-info <target>`.

---

## 🗂️ Unified Directory Listing & Inspector (v0.6: `ez list`)

`ez list` is a modern, unified replacement for `ls`, `tree`, `du`, and `stat`. It eliminates cryptic flags (`ls -la`, `tree -L 2`, `du -sh *`, `stat <file>`) in favor of clear, visual feedback and an interactive inspector.

> ⚠️ **Strictly Flagless and Pathless**: `ez list` accepts **no path argument anywhere**. You never type raw paths like `ez list /var` or `ez list my_folder`. Directories are always selected visually.

### Form 1: Instant Non-Interactive Pretty Listing (`ez list`)
Run `ez list` with no arguments for an instant pretty listing of your current directory:
```bash
ez list
```
- **Instant shell output**: Prints formatted Rich table and returns immediately to the shell (not a persistent viewer).
- **Rich file badges & emoji icons**: Every file and folder displays its contextual file-type emoji (e.g. 📁 folders, 🐍 Python, 📦 archives, 📄 documents).
- **Human-readable sizes**: Clean size formatting (`B`, `KB`, `MB`, `GB`).
- **Progressive background folder sizing**: Folder sizes are computed concurrently in the background and streamed live into the output table without blocking or delaying the initial directory listing.
- **Subtle hidden files**: Hidden dotfiles and dotfolders are visible by default with a distinct, subtle dim styling.

### Form 2: Visual Explorer + Directory Listing (`ez list choose-directory`)
To inspect any folder across your system:
```bash
ez list choose-directory
```
1. **Visual Picker**: Launches the mini file manager to visually navigate and select any directory across your filesystem (with places shortcuts, bookmarks, and search).
2. **Instant Shell Output**: Prints the pretty listing table of the chosen directory directly to your terminal shell (with file emojis, human sizes, subtle hidden items, and progressive background folder sizing).
3. **Optional Interactive TUI Inspector**: At the bottom of the listing, a prompt allows pressing `[i]` to open the full Textual TUI inspector (or pressing `Enter` to return to the shell):
   - `[t]`: **Toggle View**: Switch seamlessly between flat table list view and hierarchical collapsible tree view.
   - `[s]`: **Cycle Sorting**: Re-sort entries instantly by **Name** (A–Z) $\rightarrow$ **Size** (largest first) $\rightarrow$ **Date** (newest first).
   - `[h]`: **Toggle Hidden**: Show or hide dotfiles and dotfolders on the fly.
   - `[Enter]`: **Stat Details Modal**: Opens a comprehensive details card displaying:

     - Full path and filename with emoji icon
     - Creation timestamp and Last Modified timestamp
     - **Plain English permissions** (e.g. `You: read+write · Others: read-only` or `You: read+write+exec · Others: read+exec`)
     - Exact byte count alongside human-readable size
     - Owner username and group name
   - `[q]` / `[Esc]`: Exit inspector and return to your terminal shell.
- **Friendly Empty State**: If a directory contains no items, displays a clean, friendly notification card.
- **Loading Spinner**: Large directories display an animated loading indicator while indexing.
- **Automatic Privilege Elevation**: If an unreadable or protected folder is selected (e.g. `/root` or `/etc/ssl/private`), EasyCLI seamlessly triggers its consent elevation dialog.

---

## 🕒 Mini Timeshift System Restore Points (v0.6: ez time-machine)

`ez time-machine` is a standalone, lightweight system restore point manager inspired by Timeshift. It allows you to create point-in-time system snapshots, preview changes, safely roll back in case of system breakages, and browse snapshot files—all directly inside your terminal with **zero external software or heavy Timeshift package installations**.

> 💡 **Self-Contained & Native**: Built with standard Linux utilities (`rsync` with hardlink deduplication `--link-dest`, `cp`, and optional `btrfs`), snapshots take minimal disk space and complete in seconds.

### Form 1: Interactive Full-Screen Timeline TUI
Launch the interactive visual restore manager:
```bash
ez time-machine
```
- **Storage & Health Dashboard**: Live header showing the backup partition, total capacity, free disk space, snapshot count, and latest snapshot date.
- **Visual Restore Point Timeline**: Rich table detailing each restore point's ID, badge (`⚡ Configs` vs `🖥️ Full Root`), human-readable timestamp, size, and user description comment.
- **Keyboard & Mouse Hotkeys**:
  - `[c]`: **Create Snapshot Modal** — Enter a comment and select between `Configs (~50MB)` or `Full Root`.
  - `[r]`: **Safe Rollback Modal** — Pre-flight simulation checks, impacted folder preview, warning confirmation card.
  - `[d]`: **Delete Snapshot Modal** — Safely remove old snapshots to reclaim disk space.
  - `[b]`: **Browse Snapshot** — Opens EasyCLI's file manager inside the snapshot directory for visual file inspection.
  - `[Enter]` / `[i]`: **Snapshot Details Modal** — Detailed breakdown of captured paths, file counts, and metadata.
  - `[F5]` / `[R]`: **Refresh** — Reload live disk stats and snapshots.
  - `[q]` / `[Esc]`: Quit back to your shell.

### Form 2: Direct CLI Commands (Non-Interactive)
```bash
# Instant pretty listing table of all existing restore points
ez time-machine list

# Create a restore point directly from the shell
ez time-machine create "Before kernel update"
```

> ⚠️ **Strictly Flagless and Pathless**: `ez time-machine` accepts **no path argument anywhere**. Running `ez time-machine /var` is rejected. Folders and snapshots are always inspected and browsed visually.

---

## 🧹 Safe System Cleaner (v0.6: ez cleanup)

`ez cleanup` is an interactive, safety-first system cleaner that reclaims storage by clearing safe caches, empty trash bins, rotated logs, and orphan packages without risking system breakages.

```bash
ez cleanup
```

- **Junk Categories Scanned**:
  - `📦 APT Package Cache`: Leftover `.deb` downloads in `/var/cache/apt/archives/`.
  - `🍂 Orphan Dependencies`: Unused dependencies via `apt-get autoremove` simulation.
  - `🗑️ User Trash Bin`: Discarded files in `~/.local/share/Trash`.
  - `📜 Old Rotated Logs`: Compressed or archived logs in `/var/log` and journal archives.
  - `🖼️ Thumbnail Cache`: Obsolete cached thumbnails in `~/.cache/thumbnails`.
- **Desktop-Critical Safety Guard**:
  - Always runs a dry-run simulation first.
  - Inspects orphan packages for critical desktop components (`xorg`, `gdm3`, `sddm`, `lightdm`, `gnome-shell`, `plasma-desktop`, `dde`, `xfce4`, `ubuntu-desktop`).
  - If critical packages are detected, flags them **HIGH RISK** and defaults to offering **"Keep them via apt-mark manual"** instead of removal. Autoremoval will never run silently.
- **Interactive Flow**: Select all or specific categories by number, preview total space to be reclaimed, review confirmation prompt, track live cleaning progress, and view a final summary of freed disk space.

---

## 👤 User Profile & Password Management (v0.6: ez profile)

`ez profile` provides a comprehensive overview of your current user account and an interactive, secure password change utility.

```bash
ez profile
```

- **Account Information Card**: Displays username, full name (GECOS), account type and sudo rights status (including passwordless sudo detection), home directory, login shell, and user groups.
- **Secure Password Change (`[p]`)**:
  - Full TUI modal with current password verification.
  - New password input with dot masking (`••••`) and a `[👁️ Show Password]` / `[🙈 Hide Password]` toggle (identical to `ez connect-wifi`).
  - Re-enter password confirmation step.
  - **Arbitrary Length Support**: Zero artificial length constraints (accepts any valid password length).
  - **Zero Leakage**: Authenticates via the elevation layer and transmits the password strictly via stdin to `chpasswd`—never exposed in `sys.argv`, logs, or disk.

---

## 🔧 Package Repair Engine (v0.6: ez fix-packages)

`ez fix-packages` automatically diagnoses and resolves broken package states, replacing manual invocations of `apt --fix-broken install` and `dpkg --configure -a`.

```bash
ez fix-packages
```

- **Health Check & Diagnostics**: Inspects `dpkg --audit`, package status databases, and unresolved package dependencies.
- **All-Clear State**: If system health is optimal, displays a friendly green card confirming no broken or unconfigured packages exist.
- **Simulation Preview**: If issues are found, breaks down packages to configure, install, or remove with a clear **RISK BADGE** (`LOW`, `MEDIUM`, or `HIGH`).
- **One-Click Repair**: Prompts for consent, elevates privileges through the non-root helper, finalizes pending configurations (`dpkg --configure -a`), and repairs broken dependencies (`apt-get --fix-broken install -y`).
- **Proactive Integration**: `ez update` and `ez upgrade` automatically detect broken package states on failure and suggest running `ez fix-packages`.

---

## 🚀 Startup Apps & Boot Services Manager (v0.6: ez startup-apps)

`ez startup-apps` gives you complete, intuitive control over what programs launch at user login and what system daemons start at boot.

### Form 1: Interactive Two-Tab Manager
```bash
ez startup-apps
```
- **Tab 1: 🚀 Login Apps**:
  - Scans user autostart (`~/.config/autostart`) and system autostart (`/etc/xdg/autostart`).
  - **Root-Free Toggling**: Disabling system autostart entries creates a user-level override (`Hidden=true`) without needing administrator rights or modifying system files.
- **Tab 2: ⚙️ Boot Services**:
  - Scans enabled and disabled systemd service units.
  - Toggles units using `systemctl enable` or `systemctl disable` via the elevation layer.
- **Critical Service Safety Locking**:
  - Critical services (`NetworkManager`, `dbus`, `systemd-logind`, display managers, `ssh`, `ufw`, `pipewire`) are locked with 🔒.
  - Disabling a critical service requires explicit **typed confirmation** (`DISABLE`) to prevent accidental system lockouts.
- **Preview Line**: Each selected row explains exactly what will happen at next boot or login.

### Form 2: Direct Single-Item Inspection & Toggle
```bash
ez startup-apps discord
ez startup-apps ssh
```
- Displays a single item card showing its current state, category, command/unit path, and preview effect with an instant toggle prompt.

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
├── pyproject.toml         # Packaging configuration (v0.6.0)
├── setup.py               # Setup script (v0.6.0)
├── install.sh             # 1-step deployment script
├── README.md              # Documentation and guide
├── tests/                 # Comprehensive unit test suite (420 tests)
│   ├── test_distro.py     # Distro parser and derivative detection tests
│   ├── test_collectors.py # System inspection and installed package tests
│   ├── test_file_ops.py   # Copy, move, cross-filesystem, and conflict tests
│   ├── test_undo.py       # Reversible undo engine verification
│   ├── test_create.py     # File & folder creation validation tests (v0.3)
│   ├── test_delete.py     # Safe deletion, non-force, and consent tests (v0.3)
│   ├── test_editor.py     # Mini text & code editor validation tests (v0.3)
│   ├── test_cli.py        # CLI dispatch, flagless enforcement, and end-to-end flow tests
│   ├── test_elevation.py  # Privilege elevation & permission-denied simulation tests
│   ├── test_update_upgrade.py # Update & upgrade catalog and simulation tests (v0.4)
│   ├── test_uninstall.py  # Safe multi-source uninstallation tests (v0.4)
│   ├── test_task_manager.py # Lite & Pro Windows-style task manager tests (v0.4)
│   ├── test_version.py    # Universal version checker multi-source tests (v0.4)
│   ├── test_internet_check.py # Internet connectivity & pipeline tests (v0.5)
│   ├── test_wifi.py       # Wi-Fi scanner, password modal, and manager tests (v0.5)
│   ├── test_search_file.py # Fuzzy file search, action dispatcher & system fallback tests (v0.5)
│   ├── test_compress.py   # Multi-format compression, TUI & comma-target tests (v0.5)
│   ├── test_extract.py    # Extraction engine, formats, Zip-Slip & CLI tests (v0.5)
│   ├── test_run.py        # Universal runner, detector, safe guided mode & CLI tests (v0.5)
│   ├── test_list.py       # Unified listing, tree, permissions & inspector tests (v0.6)
│   ├── test_time_machine.py # Standalone Time Machine engine, modals & CLI tests (v0.6)
│   ├── test_cleanup.py    # Safe system cleaner & desktop-critical checks (v0.6)
│   ├── test_profile.py    # User profile & secure password change tests (v0.6)
│   ├── test_fix_packages.py # Broken package state diagnostic & repair tests (v0.6)
│   └── test_startup_apps.py # Login apps & boot services manager tests (v0.6)
└── ezcli_app/
    ├── __init__.py        # Package version (__version__ = "0.6.0")
    ├── config.py          # Declarative FeatureTemplate definitions (canonical commands only)
    ├── distro.py          # /etc/os-release parsing and Debian validation
    ├── emoji.py           # Font capability and UTF-8 detection
    ├── collectors.py      # Subprocess execution and multi-platform queries
    ├── renderers.py       # Rich visual layout and box-drawing renderers
    ├── menu.py            # Interactive TUI menu and keyboard navigation
    ├── main.py            # Subcommand parser, visual choose-directory dispatcher
    ├── list_cli.py        # Instant listing (Form 1) & background size streaming (v0.6)
    ├── list_tui.py        # Textual TUI inspector, tree/flat toggle & stat modal (v0.6)
    ├── cleanup/           # Safe System Cleaner (v0.6)
    │   ├── __init__.py    # Cleanup package exports
    │   ├── cleaner_engine.py # Scanning, trash/thumbs/apt/logs & critical guards
    │   └── cleanup_cli.py # Category selection, preview, and progress CLI
    ├── profile_cli.py     # User profile card & secure password change modal (v0.6)
    ├── fix_packages_cli.py# Broken package diagnostic & automated repair engine (v0.6)
    ├── startup_apps/      # Startup & Boot Services Manager (v0.6)
    │   ├── __init__.py    # Startup apps package exports
    │   ├── startup_engine.py # Autostart overrides, systemd units & critical locking
    │   ├── startup_app.py # Interactive Textual TUI with Login & Boot tabs
    │   └── startup_cli.py # Direct single-item mode & TUI launcher
    ├── elevation.py       # Shared privilege-elevation layer & password UX (v0.3)
    ├── privileged_helper.py# Minimal privileged helper for elevated tasks
    ├── file_engine.py     # Safe file operations, SHA256 checks, conflict policies
    ├── file_cli.py        # Interactive copy, move, paste, and undo CLI handlers
    ├── create_cli.py      # Interactive create-folder and create-file handlers (v0.3)
    ├── delete_cli.py      # Safe consent-first delete CLI handlers (v0.3)
    ├── edit_cli.py        # Modern text & code editor CLI handlers (v0.3)
    ├── undo.py            # Reversible undo history engine (~/.local/share/ez)
    ├── update_upgrade.py  # Catalog refresh, simulation & system upgrade (v0.4)
    ├── uninstall_cli.py   # Multi-source safe application uninstallation (v0.4)
    ├── task_manager.py    # Lite Windows-style terminal task manager (v0.4)
    ├── internet_checker.py# Internet connectivity diagnostic engine & pipeline (v0.5)
    ├── search_file.py     # Fuzzy file search, interactive actions & elevated fallback (v0.5)
    ├── compress_engine.py # Core compression engine (.zip, .tar.gz, .tar.xz, .7z) (v0.5)
    ├── compress_tui.py    # Textual TUI & CLI fallback format & name selector (v0.5)
    ├── compress_cli.py    # Multi-target validation, conflict & live progress CLI (v0.5)
    ├── extract_engine.py  # Core extraction engine (.zip, .tar.*, .7z, Zip-Slip guard) (v0.5)
    ├── extract_cli.py     # Direct extract-here, two-stage picker & elevation CLI (v0.5)
    ├── run_detector.py    # Target resolution hierarchy, desktop/snap/flatpak engine (v0.5)
    ├── run_guide.py       # Safe help probe, static AST script parser & guided form (v0.5)
    ├── run_cli.py         # Universal runner orchestrator, GUI detachment & elevation (v0.5)
    ├── time_machine/      # Standalone Mini Timeshift Restore Points (v0.6)
    │   ├── __init__.py    # Time Machine package exports
    │   ├── snapshot_engine.py # Native rsync hardlink deduplication & restore engine
    │   ├── time_machine_app.py# Textual TUI with timeline, modals, & stats
    │   └── time_machine_cli.py# CLI dispatcher, direct list/create & path rejection
    ├── wifi/              # Textual TUI In-Terminal Wi-Fi Manager with mouse support (v0.5)
    │   ├── __init__.py    # Wi-Fi package exports
    │   ├── wifi_engine.py # Network scanning, signal bars, security and connection engine
    │   └── wifi_app.py    # Textual TUI with mouse, password dialog, and show/hide toggle
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
  - Live system and process monitor (`ez stats`) with per-core visual CPU bars, RAM/Swap gauges, and safe process termination.
  - Non-force-first safety: non-empty folders always prompt before any force removal. Direct commands restricted to current directory.
  - 100% automatic privilege elevation with consent and visible dot password feedback (`••••`), without `--admin` flags or root contamination.
- **v0.4 — Privileged Software Catalog Updates, System Upgrade, Task Manager & Universal Version Checker**:
  - Software catalog refresh (`ez update`) with read-only explanation card, repo hit/get counts, warning tolerance, and anti-panic reminders.
  - Comprehensive multi-source system upgrade (`ez upgrade`) across APT, Flatpak, and Snap with impact simulation, Timeshift restore point recommendation, risk badge, and reboot check.
  - Safe application uninstallation (`ez uninstall <name>`) across APT, Flatpak, and Snap with warning card, single consent, and zero-cache admin elevation.
  - Lite & modern terminal Task Manager (`ez task-manager`, `ez task-manager-pro`) with mouse support, real-time gauges, unresponsive process detection, and auto-elevation.
  - Universal Version Checker (`ez version [name]`, consolidated into `ez package-info` in v0.5) automatically inspecting binaries on PATH, Debian packages, APT catalog, Snap, Flatpak, Python, and Node libraries without flags.
- **v0.5 — Internet Diagnostics, Visual Pipeline, In-Terminal Wi-Fi Manager, Fuzzy File Search, Compression, Extraction & Universal Runner**:
  - Universal internet connectivity checker (`ez check-internet`) testing Router ping, DNS resolution, and internet reachability.
  - High-contrast visual pipeline (`Router → DNS → Internet`) with latency indicators (`✔`/`✖`).
  - Immediate beginner-friendly one-line diagnostic reply explaining "Why internet isn't working" across all network failure modes.
  - In-terminal graphical Wi-Fi manager (`ez connect-wifi`) with full mouse support, real-time signal bars (`▂▄▆█ 85% 📶`), security detection, password entry modal with show/hide toggle (`👁️`/`🙈`), and action buttons (`Connect`, `Cancel`, `Refresh`, `Disconnect`).
  - Fast fuzzy file search (`ez search-file <term>`) starting from `/home`, rich results table with emoji icons, interactive selection to open, copy path, or edit, and optional system-wide (`'/'`) fallback with auto-elevation.
  - Multi-format archive compression (`ez compress`) supporting `.zip`, `.tar.gz`, `.tar.xz`, `.7z`, and `.tar.bz2` with TUI format selector, comma-separated multi-item targeting in current directory, `choose-directory` mini explorer picker, live progress, and success summary.
  - Safe archive extraction (`ez extract-here` and `ez extract choose-directory`) supporting `.zip`, `.tar.gz`, `.tar.xz`, `.7z`, `.tar.bz2`, `.tar` with Zip-Slip path traversal protection, live extraction progress, multi-file comma targeting, two-stage visual picker, and automatic elevated destination support.
  - Universal Application & Script Runner (`ez run <target> [args...]`) executing local scripts, binaries, AppImages, and installed applications (PATH, Snap, Flatpak, Desktop entries). Features detached background launch for GUI apps, foreground execution for CLI tools, safe flag-free Guided Mode with preview confirmation, and automatic privilege elevation.

- **v0.6 — Unified Directory Listing, Mini Timeshift & System Maintenance**:
  - Flagless and pathless unified directory listing and inspector (`ez list`, `ez list choose-directory`) replacing `ls`, `tree`, `du`, and `stat` with instant pretty table, progressive background folder sizing, tree view toggle, and plain English permissions modal.
  - Standalone Mini Timeshift System Restore Points (`ez time-machine`) with zero external software dependencies, rsync hardlink deduplication (`--link-dest`), dual profiles (`Configs` vs `Full Root`), interactive timeline TUI, create restore point modal (`c`), safe rollback with pre-flight simulation (`r`), delete modal (`d`), visual snapshot browsing (`b`), and direct CLI list/create commands.
  - Safe system cleaner (`ez cleanup`) scanning APT cache, orphan packages with desktop-critical protection (`xorg`, display managers, desktop metapackages), user trash, rotated logs, and thumbnail caches.
  - User profile & password management (`ez profile`) displaying full user info and modern TUI password change modal with dot feedback and show/hide toggle matching `ez connect-wifi`.
  - Broken package state repair (`ez fix-packages`) replacing manual `apt --fix-broken install` and `dpkg --configure -a` with simulation preview, risk badges, and elevated repair execution.
  - Startup applications & boot services manager (`ez startup-apps`) providing an interactive 2-tab TUI with root-free autostart overrides, elevated systemd toggles, and typed confirmation locks on critical services.

---

## 🧪 Running Tests

To run the automated unit test suite:
```bash
python3 -m unittest discover tests/
```

All 420 unit tests validate distro detection, collector safety, file operations, conflict policies, cross-filesystem moves, undo engine, command parsing, file/folder creation, safe deletion with force prompts, mini text editor validation, binary file protection, permission-denied simulations, live stats metrics, privileged catalog updates, multi-source system upgrade simulations, safe application uninstallation, Windows-style task manager, universal version checking, internet connectivity diagnostics, in-terminal Wi-Fi management, multi-format compression, safe archive extraction, universal application execution with safe guided mode, unified directory listing with background folder sizing, standalone Time Machine snapshot engine and modals, safe system cleaner with desktop-critical guards, user profile card and secure password updating, broken package repair diagnostics, and startup applications/boot services management.


