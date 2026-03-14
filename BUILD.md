# Building Bazaar Overlay

This guide covers how to build the Bazaar Overlay application into a distributable Windows executable.

## Prerequisites

- Windows 10/11
- Python 3.11+
- Git (for cloning)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/huskerwin/BazaarOverlay.git
cd BazaarOverlay
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Test the Application

```bash
python main.py
```

Hold `Shift+E` over an item in the game to see the overlay.

### 3. Build Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller build.spec
```

The executable will be in `dist/BazaarOverlay/BazaarOverlay.exe`

### 4. Create Installer (Optional)

```bash
# Install Inno Setup from https://jrsoftware.org/isinfo.php
# Then compile the installer:
iscc installer.iss
```

The installer will be in `installer/BazaarOverlay-Setup-1.0.0.exe`

---

## Build Options

### PyInstaller Options

The `build.spec` file contains the build configuration. Key options:

| Option | Description |
|--------|-------------|
| `--onefile` | Single executable (default) |
| `--windowed` / `-w` | No console window |
| `--icon=icon.ico` | App icon |
| `--name=BazaarOverlay` | Executable name |

### Build Commands

```bash
# Clean build
pyinstaller build.spec --clean

# Build with UPX compression (if UPX installed)
pyinstaller build.spec --upx-dir PATH_TO_UPX
```

---

## Project Structure

```
BazaarOverlay/
├── main.py                 # Application entry point
├── build.spec              # PyInstaller configuration
├── installer.iss           # Inno Setup script
├── version_info.txt         # Executable metadata
├── assets/
│   ├── icon.ico           # App icon (256x256)
│   └── icon.png           # Icon preview
├── overlay_app/
│   ├── settings_manager.py # Persistent settings
│   └── settings_window.py  # Settings UI
├── data/
│   ├── items.json         # Item database
│   └── enchantments.json  # Enchantment data
└── dist/                  # Build output
    └── BazaarOverlay/
        └── BazaarOverlay.exe
```

---

## Troubleshooting

### PyInstaller Issues

**Missing modules:**
```bash
# Add to hiddenimports in build.spec
pyinstaller build.spec --hidden-import=module_name
```

**Large file size:**
- Normal size: ~100-200MB (includes Python + OCR runtime)
- Use `--exclude-module` to remove unused packages

**Antivirus false positives:**
- The exe may be flagged by some antivirus
- Consider code signing (requires certificate)
- Submit to Microsoft Defender for analysis

### Application Issues

**App doesn't start:**
- Check `dist/BazaarOverlay/` folder has all files
- Run from command line to see error messages

**No items loaded:**
- Ensure `data/items.json` is included in the build
- Check the spec file's `datas` section

**System tray not showing:**
- Ensure icon file is included
- Check Windows notification settings

---

## Distribution

### GitHub Releases

1. Build the executable
2. Create a GitHub Release
3. Upload:
   - `dist/BazaarOverlay/BazaarOverlay.exe` (portable)
   - `installer/BazaarOverlay-Setup-1.0.0.exe` (installer)

### Portable Version

Users can run `BazaarOverlay.exe` directly without installation.

### Installer

The Inno Setup installer:
- Installs to Program Files
- Creates Start Menu shortcuts
- Creates Desktop shortcut (optional)
- Includes uninstaller

---

## Development Notes

### Adding New Dependencies

1. Install the package
2. Test with `python main.py`
3. Add to `requirements.txt`
4. Update `build.spec` hiddenimports if needed
5. Rebuild

### Modifying the UI

- Settings window: `overlay_app/settings_window.py`
- Overlay display: `overlay_app/overlay_window.py`

### Testing the Build

```bash
# Test the built executable
dist\BazaarOverlay\BazaarOverlay.exe
```

---

## Version History

- **1.0.0** - Initial release
  - OCR-based item detection
  - Enchantment display
  - System tray integration
  - Settings window
  - Installer support
