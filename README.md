# Bazaar Overlay (Windows)

OCR-based item info overlay for games.

## What this app does

- Listens globally for `Shift + E` hold
- Captures screen around cursor
- Uses OCR (EasyOCR) to read item names from game UI
- Matches text against items database
- Shows overlay in top-right of screen with item info

This app does **not** automate gameplay or interact with the game beyond screen capture.

## Requirements

- Windows 10/11
- Python 3.11+
- Game running in borderless/windowed mode

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Run

**Normal mode:**
```bash
python main.py
```

**Debug mode (shows OCR region):**
```bash
python main.py --debug
```

Hold `Shift + E` over an item in the game to see its info.

## Command Line Options

| Option | Default | Description |
|--------|---------|--------------|
| `--debug` | off | Show debug overlay with OCR region |
| `--roi-radius` | 400 | Capture radius around cursor (pixels) |
| `--poll-ms` | 75 | Detection loop interval (ms) |
| `--skip-frames` | 1 | Skip OCR every N frames |
| `--ocr-region` | 0,0,0,0 | OCR region (x,y,width,height), 0=full |
| `--items` | data/items.json | Path to items database |

### Performance tips

- Smaller `--roi-radius` = faster (400 is default, try 200)
- Higher `--skip-frames` = faster (2 = half speed, 3 = third speed)

Example for better performance:
```bash
python main.py --debug --roi-radius 200 --skip-frames 2
```

## Shortcuts

- `Run Bazaar Overlay.cmd` - Normal mode
- `Run Bazaar Overlay (Debug).cmd` - Debug mode

## Item Database

Edit `data/items.json`:

```json
{
  "items": [
    {
      "id": "health_potion",
      "name": "Health Potion",
      "info": "Restores 50 HP",
      "enabled": true
    }
  ]
}
```

Fields:
- `id` - unique identifier (optional)
- `name` - displayed name (used for OCR matching)
- `info` - description shown in overlay
- `enabled` - include/exclude from matching

## Documentation

- `docs/ARCHITECTURE.md` - System design and module responsibilities
- `docs/DEVELOPER_GUIDE.md` - Detailed developer documentation

## Project Structure

```
overlay_app/
  controller.py    - Main orchestration
  ocr_detector.py - OCR text detection
  screen_capture.py - Screen capture
  hotkey_listener.py - Keyboard input
  overlay_window.py - UI rendering
  config.py - Configuration
  models.py - Data classes
  item_repository.py - Item database loading

tools/
  capture_template.py - Template capture tool

data/
  items.json - Item definitions
```

## How It Works

1. User holds Shift+E
2. App captures screen region around cursor
3. EasyOCR extracts text from capture
4. Text is matched against item names (fuzzy matching)
5. Matched item info shown in overlay (top-right)
6. User releases Shift+E, overlay hides
