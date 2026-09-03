# EasyCLI (`ezcli`) v0.1

**EasyCLI** is a terminal-based frontend wrapper for common Linux commands built specifically for beginners on Debian-based systems. It wraps complex and verbose Linux commands into clean, color-coded, and intuitive terminal cards and tables.

---

## 🎯 Target Platforms

EasyCLI is tailored for Debian-based distributions:
- **Debian**
- **Ubuntu**
- **Zorin OS**
- **Deepin**
- **UbuntuDDE**
- Linux Mint, Pop!_OS, Elementary OS, and other Debian/Ubuntu derivatives.

Distributions are automatically detected via `/etc/os-release` and verified for standard Debian utilities (`apt`, `dpkg`, and `systemd`).

---

## 🛡️ Strict v0.1 Read-Only Guarantee

**v0.1 is 100% read-only:**
- Never modifies system configuration, services, networks, users, or files.
- Never requires root privileges or invokes `sudo`.
- Never writes caches or creates temporary state files.
- Command execution is strictly defensive: missing tools, empty outputs, or permission limits are handled gracefully with friendly explanations rather than tracebacks.

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
├── ezcli                  # Executable entrypoint script
├── pyproject.toml         # Packaging configuration
├── README.md              # Documentation and guide
├── tests/                 # Unit test suite
│   ├── test_distro.py     # Distro parser and derivative detection tests
│   ├── test_collectors.py # Defensive data collection tests
│   └── test_cli.py        # CLI dispatch and argument validation tests
└── ezcli_app/
    ├── __init__.py        # Package version
    ├── config.py          # Declarative FeatureTemplate definitions
    ├── distro.py          # /etc/os-release parsing and Debian validation
    ├── emoji.py           # Font capability and UTF-8 detection
    ├── collectors.py      # Read-only defensive subprocess execution wrappers
    ├── renderers.py       # Rich visual layout and box-drawing renderers
    ├── menu.py            # Interactive TUI menu and navigation
    └── main.py            # Subcommand parser and dispatcher
```

### Adding New Features for v0.2
To add a new subcommand:
1. Define a `FeatureTemplate` in `ezcli_app/config.py`.
2. Add a read-only collector in `ezcli_app/collectors.py`.
3. Add a Rich renderer in `ezcli_app/renderers.py`.
4. Register the renderer in `ezcli_app/main.py` and `ezcli_app/menu.py`.

---

## 🧪 Running Tests

To run the automated unit test suite:
```bash
python3 -m unittest discover tests/
```

All 22 unit tests validate distro detection, collector safety, command parsing, and CLI flags.
