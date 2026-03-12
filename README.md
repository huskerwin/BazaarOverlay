# Bazaar Overlay MVP (Windows)

This project provides a desktop overlay that appears when you hold `Shift + E`.
While the hotkey is held, it captures a region around your cursor, compares that image against known templates, and displays item information near your cursor.

## What this app does

- Listens globally for `Shift + E` hold.
- Captures a small region around the mouse cursor.
- Runs a hybrid OpenCV pipeline (template shortlist + ORB verification + short temporal smoothing).
- Shows a transparent, always-on-top, click-through overlay.
- Displays match confidence and falls back to `No confident match found.`

This app does **not** automate gameplay or interact with the game client beyond screen capture and local overlay display.

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

```bash
python main.py
```

Hold `Shift + E` over an item icon to trigger detection.

Useful flags:

```bash
python main.py --debug --roi-radius 72 --poll-ms 75 --threshold 0.80
```

Note: if `--roi-radius` is smaller than your largest template, the app automatically increases it at runtime.

### OCR Mode (Alternative Detection)

The app supports two detection modes:

1. **Template Matching** (default) - Uses image matching against template files
2. **OCR Mode** - Uses OCR to read item names from the game hover text

OCR mode is faster when you have many templates. To use OCR mode:

```bash
python main.py --ocr --debug
```

Configure the OCR region to match where item names appear in the game:

```bash
python main.py --ocr --debug --ocr-region "50,30,200,40"
```

The `--ocr-region` format is `x,y,width,height` (pixels relative to cursor). Use `--debug` to visualize the green OCR capture box while configuring.

Switch between modes:
- Template matching: `--ocr` flag absent
- OCR mode: `--ocr` flag present

## One-click launchers (Windows)

- `Run Bazaar Overlay.cmd` - starts the overlay app.
- `Run Capture Template.cmd` - prompts for item info, then starts template capture in `hotkey-box` mode.
- `tools/create_shortcut.ps1` - creates desktop shortcuts for both launchers (`Bazaar Overlay.lnk` and `Bazaar Capture Template.lnk`).

Create/refresh desktop shortcuts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/create_shortcut.ps1
```

## Item database format

`data/items.json`

```json
{
  "items": [
    {
      "id": "iron_sword",
      "name": "Iron Sword",
      "template": "assets/templates/iron_sword.png",
      "threshold": 0.82,
      "info": "Common melee weapon"
    }
  ]
}
```

Supported fields:

- `id` (optional but recommended)
- `name` (required)
- `template` (single image path)
- `templates` (optional list of image paths)
- `enabled` (optional boolean, set `false` to keep an item in the file but exclude it from matching)
- `threshold` (optional per-item confidence threshold)
- `info` (optional text shown in overlay)

## Capture your own templates quickly

Use the helper tool while your game is open:

```bash
python tools/capture_template.py iron_sword --threshold 0.82 --name "Iron Sword"
```

By default, the tool waits for `Shift+C`, takes a screenshot, then opens a selector where you draw a box and press Enter/Space to confirm.

Hotkey-box workflow:

1. Run the command.
2. Focus the game.
3. Press `Shift+C`.
4. Drag a selection box.
5. Press Enter/Space to confirm (`Esc` cancels).

If you prefer the old cursor-centered square capture mode:

```bash
python tools/capture_template.py iron_sword --mode cursor --countdown 3 --size 56 --threshold 0.82 --name "Iron Sword"
```

The tool saves `assets/templates/iron_sword.png` and prints a JSON snippet to paste into `data/items.json`.

## Project layout

- `overlay_app/` - main application modules (hotkey, capture, matcher, UI, controller).
- `tools/` - helper scripts (`capture_template.py`, `create_shortcut.ps1`).
- `assets/templates/` - template image files used for matching.
- `data/items.json` - item manifest and metadata.
- `tests/` - unit tests for repository loading and template matching.
- `Run Bazaar Overlay.cmd` / `Run Capture Template.cmd` - click-to-run entry points for Windows.

## Tuning tips

- Start with 15-30 templates for near real-time response.
- If false positives occur, increase threshold for specific items.
- If misses occur due to scale differences, keep item icon size stable and add extra templates for that item.
- ROI size (`--roi-radius`) is the biggest speed/accuracy tradeoff.
- If templates are large (wide buttons/icons), keep captures tight, or expect higher CPU due to a larger effective ROI.
- Default matching uses top `3` shortlist candidates and ORB re-ranking; tune `MatchConfig` in `overlay_app/config.py` for stricter or faster behavior.
- Temporal smoothing defaults to `2` stable frames before a positive match; increase if labels flicker.

## Key files

- `main.py` - app entry point
- `overlay_app hotkey to capture/controller.py` -/match/render orchestration
- `overlay_app/template_matcher.py` - hybrid matching engine (template shortlist + ORB re-ranking)
- `overlay_app/ocr_detector.py` - OCR-based item detection using EasyOCR
- `overlay_app/overlay_window.py` - transparent overlay rendering
- `overlay_app/item_repository.py` - JSON item database loader
- `overlay_app/config.py` - configuration dataclasses
- `tools/capture_template.py` - template capture helper
- `tools/scrape_bazaardb_items.py` - BazaarDB item image scraper for building template libraries

## Scraping item templates

Use this when you want to download publicly visible item images from BazaarDB into a local `templates/` folder.

Install scraper dependencies:

```bash
pip install -r requirements-scraper.txt
playwright install chromium
```

Inspect rendering mode (helps confirm static vs dynamic loading):

```bash
python tools/scrape_bazaardb_items.py --inspect-only
```

Run scraper (auto mode picks Playwright when needed):

```bash
python tools/scrape_bazaardb_items.py --mode auto --templates-dir templates
```

Useful options:

- `--limit 50` for quick dry-runs
- `--download-delay 0.25` for slower rate limiting
- `--metadata-csv templates/items.csv --metadata-json templates/items.json`
- `--insecure` only if your local environment has TLS certificate issues

What the scraper writes:

- `templates/<sanitized_item_name>.png`
- metadata files with item name, source page URL, image URL, local filename, and status (`downloaded`/`skipped`/`failed`)

## Architecture documentation

- `docs/ARCHITECTURE.md` - system design, module responsibilities, runtime flow, and extension points

## Known limitations

- Template matching can confuse visually similar icons.
- Exclusive fullscreen and anti-cheat protections may block capture/overlay behavior.
- Very large template libraries may increase CPU usage and latency.
