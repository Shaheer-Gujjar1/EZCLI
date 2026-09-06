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

| Icon | Subcommand & Syntax | Version | Wrapped Tools | Description |
| :---: | :--- | :---: | :--- | :--- |
| 💻 | `ez system-info` | **v0.1** | `hostnamectl`, `uptime -p`, `/etc/os-release` | Key-value card with OS name/version, hostname, kernel, architecture, and uptime. |
| ⚡ | `ez stats` | **v0.3** | `/proc`, `ps`, `free`, `uptime` | Live-updating system & process monitor (modern `htop` alternative with per-core CPU bars, RAM/Swap gauges, search filtering, and safe process termination). |
| 📋 | `ez task-manager` | **v0.4** | *(Windows Task Manager)*, `ps`, `kill` | Lite & modern Windows-style task manager for user apps with mouse support, emoji icons, unresponsive detection, and instant termination. |
| 🛡️ | `ez task-manager-pro` | **v0.4** | `ps aux`, `top`, `sudo kill` | Comprehensive pro task manager with user apps, background daemons, system services, category tabs, and auto admin elevation. |
| 💽 | `ez disk-info` | **v0.1** | `df -h` | Table of storage mounts, sizes, used/available space, and inline usage bars (filters out pseudo-filesystems). |
| 📁 | `ez big-files [path \| choose-directory]` | **v0.1** | `du -h --max-depth=1`, `find` | Table of largest files and folders. Provide a path or use `choose-directory` to pick visually via the mini explorer. Defaults to `~`. |
| 🔍 | `ez package-search <term>` | **v0.1** | `apt search`, `flathub`, `snapcraft` | Universal search across **APT 📦**, **Flatpak 🟣**, and **Snap 🟢** with interactive platform selection & installation commands. |
| 📦 | `ez package <name>` | **v0.1** | `apt show`, `dpkg -s` | Card showing package version, size, homepage, description, and installed status. |
| 🔄 | `ez available-updates` | **v0.1** | `apt list --upgradable` | Table of upgradable packages and versions using existing lists only (never runs `apt update`). |
| 🔄 | `ez update` | **v0.4** | `apt update`, `apt-get update` | Refresh package catalog from repositories without installing or modifying software. Safe elevation. |
| ⬆️ | `ez upgrade` | **v0.4** | `apt upgrade`, `snap refresh`, `flatpak update` | Comprehensive upgrade across APT, Flatpak, and Snap with impact simulation, Timeshift restore point prompt, and reboot check. |
| 🗑️ | `ez uninstall <name>` | **v0.4** | `apt remove`, `snap remove`, `flatpak uninstall` | Safe application uninstallation across APT, Flatpak, and Snap with warning card, single consent, and zero-cache admin elevation. |
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
| ℹ️ | `ez version [name]` | **v0.4** | `which`, `dpkg`, `apt`, `snap`, `flatpak`, `python`, `node` | Universal version checker across PATH binaries, Debian packages, APT catalog, Snap, Flatpak, Python, and Node libraries. Dual mode: displays EasyCLI version with no argument, or inspects specified target. |
| 📶 | `ez check-internet` | **v0.5** | `ping`, `ip route`, `socket` | 3-stage visual connectivity pipeline (`Router → DNS → Internet`) with latency (`✔`/`✖`) and an immediate "Why internet isn't working" one-line diagnostic verdict. |
| 📶 | `ez connect-wifi` | **v0.5** | `nmcli`, `iw` | In-terminal graphical Wi-Fi manager with mouse support, signal strength bars, network scanning, password entry modal with show/hide toggle (`👁️`/`🙈`), and action buttons (`Connect`, `Cancel`, `Refresh`, `Disconnect`). |
| 🔍 | `ez search-file <term>` | **v0.5** | `find`, `locate`, `ls` | Fast fuzzy file search starting from `/home`, rich results table with emoji icons, interactive selection to open, copy path, or edit, and optional system-wide (`'/'`) fallback with auto-elevation. |

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

### 5. `ez version [name]` — Universal Version Checker
A single, flagless, beginner-friendly version checker for any application, package, binary, or library:
```bash
ez version         # Displays EasyCLI version + usage hint
ez version curl    # Universal inspection across all 7 sources
```
- **Dual Invocation**:
  - **No argument (`ez version`)**: Displays EasyCLI's own version along with a clear one-line tip on inspecting any external software.
  - **With argument (`ez version <name>`)**: Automatically inspects the target across all 7 detection sources in exact sequence:
    1. **Executable on PATH**: Quietly probes standard candidate version flags (`--version`, `-v`, `-V`, `version`, `-version`) with execution timeouts and safety guards.
    2. **Installed Debian Package**: Queries `dpkg-query` and retrieves installation timestamp from `/var/lib/dpkg/info/<pkg>.list`.
    3. **APT Catalog**: Checks candidate versions available via repository catalog (`apt-cache policy`).
    4. **Snap Package**: Inspects installed snaps via `snap list` and `/snap/<name>/current` mtime.
    5. **Flatpak Application**: Inspects installed Flatpaks via `flatpak info` and `flatpak list --app`.
    6. **Python Library**: Discovers installed Python packages via standard `importlib.metadata.distribution`.
    7. **Node.js Library**: Scans global npm packages (`npm root -g`) and local `./node_modules/<name>/package.json`.
- **Unified Multi-Source Card**: If a tool is present in multiple places (e.g. `curl` installed as both a system binary and Debian package), all matches are rendered together in a single, clear Rich card with Source Type, Detected Version, Identifier/Path, and Install Date.
- **Friendly Guidance**: If nothing is found across any source, renders a helpful card suggesting `ez package-search <name>` and `ez installed-packages`.
- **Read-Only & Flagless**: Zero administrative elevation needed; strictly flagless.

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
├── pyproject.toml         # Packaging configuration (v0.5.0)
├── setup.py               # Setup script (v0.5.0)
├── install.sh             # 1-step deployment script
├── README.md              # Documentation and guide
├── tests/                 # Comprehensive unit test suite (260 tests)
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
│   └── test_search_file.py # Fuzzy file search, action dispatcher & system fallback tests (v0.5)
└── ezcli_app/
    ├── __init__.py        # Package version (__version__ = "0.5.0")
    ├── config.py          # Declarative FeatureTemplate definitions (canonical commands only)
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
    ├── update_upgrade.py  # Catalog refresh, simulation & system upgrade (v0.4)
    ├── uninstall_cli.py   # Multi-source safe application uninstallation (v0.4)
    ├── task_manager.py    # Lite Windows-style terminal task manager (v0.4)
    ├── version_checker.py # Universal multi-source version detector & renderer (v0.4)
    ├── internet_checker.py# Internet connectivity diagnostic engine & pipeline (v0.5)
    ├── search_file.py     # Fuzzy file search, interactive actions & elevated fallback (v0.5)
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
  - Universal Version Checker (`ez version [name]`) automatically inspecting binaries on PATH, Debian packages, APT catalog, Snap, Flatpak, Python, and Node libraries without flags.
- **v0.5 — Internet Diagnostics, Visual Pipeline, In-Terminal Wi-Fi Manager & Fuzzy File Search**:
  - Universal internet connectivity checker (`ez check-internet`) testing Router ping, DNS resolution, and internet reachability.
  - High-contrast visual pipeline (`Router → DNS → Internet`) with latency indicators (`✔`/`✖`).
  - Immediate beginner-friendly one-line diagnostic reply explaining "Why internet isn't working" across all network failure modes.
  - In-terminal graphical Wi-Fi manager (`ez connect-wifi`) with full mouse support, real-time signal bars (`▂▄▆█ 85% 📶`), security detection, password entry modal with show/hide toggle (`👁️`/`🙈`), and action buttons (`Connect`, `Cancel`, `Refresh`, `Disconnect`).
  - Fast fuzzy file search (`ez search-file <term>`) starting from `/home`, rich results table with emoji icons, interactive selection to open, copy path, or edit, and optional system-wide (`'/'`) fallback with auto-elevation.

---

## 🧪 Running Tests

To run the automated unit test suite:
```bash
python3 -m unittest discover tests/
```

All 235 unit tests validate distro detection, collector safety, file operations, conflict policies, cross-filesystem moves, undo engine, command parsing, file/folder creation, safe deletion with force prompts, mini text editor validation, binary file protection, permission-denied simulations, live stats metrics, privileged catalog updates, multi-source system upgrade simulations, safe application uninstallation, Windows-style task manager, universal version checking, internet connectivity diagnostics, and in-terminal Wi-Fi management.
