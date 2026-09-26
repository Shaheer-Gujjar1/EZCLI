# Changelog

All notable changes to the **EasyCLI (`ez`)** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.6.0] - 2026-09-26

### Added
- **Mini Timeshift System Restore Points (`ez time-machine`)**:
  - Zero-dependency snapshot system using `rsync` hardlink deduplication (`--link-dest`).
  - Dual backup profiles: `Configs` (user configs, `/etc`, `/home`) and `Full Root` (entire system excluding virtual mounts).
  - Interactive timeline TUI with creation modal (`c`), safe rollback with pre-flight simulation (`r`), snapshot visual file browsing (`b`), and deletion modal (`d`).
  - In-TUI administrative elevation dialog with masked password input and mouse action buttons.
  - Direct CLI commands: `ez time-machine list`, `ez time-machine create [name]`.
- **Unified Directory Listing & Inspector (`ez list`)**:
  - Flagless, pathless directory inspector replacing `ls`, `tree`, `du`, and `stat`.
  - Rich interactive table view with progressive background folder sizing calculations.
  - Tree-view toggle and plain-English file permission explanations modal.
  - Interactive directory picker support (`ez list choose-directory`).
- **Safe System Cleaner (`ez cleanup`)**:
  - Diagnostic scan and cleanup for APT cache, unused dependencies, rotated system logs, user trash, and thumbnail caches.
  - Built-in desktop-critical guards protecting against accidental removal of Xorg, display managers, and core desktop metapackages.
- **User Profile & Password Management (`ez profile`)**:
  - Comprehensive user account and privilege inspection card.
  - Modern interactive TUI password changing modal with masked dot feedback (`••••`) and show/hide toggle.
- **Broken Package State Repair (`ez fix-packages`)**:
  - Diagnostic inspection and repair wrapping `apt --fix-broken install` and `dpkg --configure -a`.
  - Impact simulation preview, risk level badges, and elevation handling.
- **Startup Applications & Boot Services Manager (`ez startup-apps`)**:
  - Interactive 2-tab TUI managing user desktop autostart entries (`~/.config/autostart`) and system services (`systemd`).
  - Root-free overrides for desktop entries.
  - Typed confirmation locks protecting critical system services against accidental disablement.
- **Windows-Style Standalone Setup Wizard**:
  - Self-extracting single-file installer script (`ez-setup.sh`) embedding the full application payload as compressed Base64.
  - Full-featured Textual graphical TUI Setup Wizard (`SetupWizardApp`) with responsive layouts, 3D button styling, and full mouse support.
  - 1-command online setup via `curl` / `wget` requiring no Git clone or prior dependencies.
  - Standalone uninstaller script (`uninstall.sh`) for clean removals.
- **CI & Licensing**:
  - Official MIT License added to repository.
  - GitHub Actions CI workflow testing on Ubuntu with Python 3.12.

### Changed
- Replaced standalone version checker with consolidated `ez package-info` and `ez list`.
- Polished Setup Wizard footer styling, responsive boundaries, and mouse hitboxes.
- Removed post-setup auto-launch prompt for a cleaner terminal handoff.

---

## [0.5.0] - 2026-09-07

### Added
- **Internet Connectivity Diagnostics (`ez check-internet`)**:
  - 3-stage visual connectivity pipeline testing Router Gateway, DNS Resolution, and Internet reachability.
  - Immediate beginner-friendly one-line verdict diagnosing exact network failure causes.
- **In-Terminal Graphical Wi-Fi Manager (`ez connect-wifi`)**:
  - Full mouse-supported Textual interface for scanning and connecting to wireless networks.
  - Real-time signal strength indicators (`▂▄▆█`) and security protocol detection.
  - Interactive password entry modal with show/hide password toggle (`👁️`/`🙈`).
- **Fuzzy File Search (`ez search-file <term>`)**:
  - Fast file search scoped to `/home` with formatted results table and emoji file icons.
  - Interactive action dispatcher to open, edit, or copy file paths.
  - Automatic elevated fallback to system-wide search (`/`) when requested.
- **Archive Compression (`ez compress`)**:
  - Multi-format archive creation supporting `.zip`, `.tar.gz`, `.tar.xz`, `.7z`, and `.tar.bz2`.
  - Interactive TUI format selector, comma-separated multi-item target inputs, and live progress bars.
  - Directory picker integration (`ez compress choose-directory`).
- **Archive Extraction (`ez extract`, `ez extract-here`)**:
  - Multi-format archive extraction with two-stage picker or current-directory extraction.
  - Built-in Zip-Slip path traversal vulnerability protection.
  - Automatic elevation support when extracting into protected directories.
- **Universal Application & Script Runner (`ez run <target> [args...]`)**:
  - Target detector resolving local scripts, binaries, AppImages, and installed applications (PATH, Flatpak, Snap, Desktop entries).
  - Safe flag-free Guided Mode with AST script parsing, command preview, and explicit confirmation.
  - Automatic background detachment for GUI applications and foreground execution for CLI tools.
- **App-Store Style Package Inspector (`ez package-info <name>`)**:
  - Simultaneous inspection across local binaries, Debian packages, APT repository catalog, Flatpak, Snap, Python (pip), and Node (npm).
  - Classification of package nature and direct safe action triggers (Run/Install/Uninstall).

### Changed
- Refactored `ez list-installed-packages` to provide interactive multi-source category filtering (`apps`, `packages`, or `both`).
- Consolidated archive extraction commands and extraction helper utilities.

---

## [0.4.0] - 2026-09-06

### Added
- **Software Catalog Refresh (`ez update`)**:
  - Beginner-friendly APT repository index refresh with read-only explanation card.
  - Repository hit/get counter statistics and anti-panic reminders for third-party repository warnings.
- **Multi-Source System Upgrade (`ez upgrade`)**:
  - Unified system-wide package upgrades covering APT, Flatpak, and Snap.
  - Pre-upgrade impact simulation, risk level badges, Timeshift restore point suggestions, and reboot detection.
  - Streaming progress updates and phase status reporting during execution.
- **Safe Application Uninstallation (`ez uninstall <name>`)**:
  - Multi-source package removal with confirmation warning cards and single-consent elevation.
- **Interactive Terminal Task Manager (`ez task-manager`, `ez task-manager-pro`)**:
  - Real-time system monitoring with per-core CPU usage bars, RAM gauges, and swap metrics.
  - Mouse-friendly process table with unresponsive process detection, sorting, and safe termination signals.
- **Live System Monitor (`ez stats`)**:
  - Modern live-updating resource dashboard.
- **Universal Version Checker (`ez version [name]`)**:
  - Zero-flag version detection across CLI binaries, system packages, and language environments.
- **Comprehensive Documentation**:
  - Added `COMMANDS_GUIDE.md` detailing the Universal Dual-Mode Architecture and Linux command replacement matrix.

### Changed
- Enforced strict flagless CLI architecture: all subcommands reject conventional UNIX flags and use guided arguments.
- Standardized privilege elevation session flow with upfront credential verification and automatic sudo cache cleanup.

---

## [0.3.0] - 2026-09-05

### Added
- **Safe File & Directory Creation (`ez create-file`, `ez create-folder`)**:
  - Modern replacements for `touch` and `mkdir` with strict current-directory scoping to prevent unintended writes.
  - Interactive item creation modal inside the file explorer (`[n]`) with auto-elevation.
- **Consent-First File Deletion (`ez delete`, `ez delete choose-directory`)**:
  - Safe replacement for `rm` and `rm -rf` demanding explicit confirmation before touching files.
  - Non-force-first logic: non-empty directories always prompt for consent.
  - Visual deletion picker mode inside the terminal file explorer (`run_delete_picker`).
- **Integrated Mini Code & Text Editor (`ez edit-file`)**:
  - Lightweight terminal text editor replacing `nano` and `vim`.
  - Syntax highlighting, line numbers, status bar, and unsaved changes safety prompt.
  - Mouse controls, theme/syntax selector modals, and line jump navigation.
- **Automatic Privilege Elevation Engine**:
  - Transparent privilege escalation for protected file operations without running the entire CLI under `sudo`.
  - Interactive terminal password prompt with masked dot feedback (`••••`).

### Changed
- Renamed primary CLI entry point from `ezcli` to `ez`.
- Allowed direct target file and directory path arguments for file manipulation commands.
- Streamlined editor UI layout with compact single-line headers and action buttons.

---

## [0.2.0] - 2026-09-04

### Added
- **Graphical Terminal File Explorer (`ez choose-directory`)**:
  - Full-screen Textual file manager with bookmark navigation, breadcrumb path display, and subshell launching.
  - Multi-select visual file tagging for batch operations.
- **Safe Copy & Move Engine**:
  - Direct file/folder arguments support (`ez copy <src> [dest]`, `ez move <src> [dest]`).
  - Pre-write inspection avoiding accidental overwrites.
  - Conflict resolution policies: `ask`, `skip`, `overwrite`, and `rename`.
  - SHA-256 and size verification for cross-filesystem move operations before removing source files.
- **Reversible Undo Engine (`ez undo`)**:
  - Transaction-backed undo engine restoring files from the most recent copy or move action.
  - Safe cleanup ensuring pre-existing destination files are never deleted on undo.
- **Clipboard Workflow**:
  - Visual staging and paste workflow with progress bars.

### Fixed
- Enforced Textual compatibility checks and backward-compatible import handling for virtual environments.

---

## [0.1.0] - 2026-09-03

### Added
- Initial project release with 12 read-only system diagnostic subcommands:
  - `ez system-info` - OS, kernel, hostname, and uptime summary.
  - `ez stats` - CPU, memory, and top processes snapshot.
  - `ez disk-info` - Filesystem mount points and storage consumption.
  - `ez big-files` - Fast discovery of large files in user home.
  - `ez network-info` - IP addresses, active interfaces, and routing table.
  - `ez logs` - Recent boot and systemd error logs.
  - `ez ports` - Listening network ports and associated services.
  - `ez services` - Systemd service statuses.
  - `ez hardware` - CPU, RAM, and motherboard details.
  - `ez usb` - Connected USB devices.
  - `ez pci` - PCI devices and controllers.
- Cross-platform package queries for **APT**, **Flatpak**, and **Snap**.
- Package search aggregator with interactive package details (`ez package-search`).
- Installed software listings with filtering (`ez list-installed-packages`).
- Automated Debian/Ubuntu setup and installer scripts.
- Rich-based terminal UI with color-coded diagnostic cards and interactive menus.
