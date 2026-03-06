# Bazaar Overlay MVP (Windows)

This project provides a desktop overlay that appears when you hold `Shift + E`.
While the hotkey is held, it captures a region around your cursor, compares that image against known templates, and displays item information near your cursor.

## What this app does

- Listens globally for `Shift + E` hold.
- Captures a small region around the mouse cursor.
- Runs OpenCV template matching against your item database.
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
- `threshold` (optional per-item confidence threshold)
- `info` (optional text shown in overlay)

## Capture your own templates quickly

Use the helper tool while your game is open:

```bash
python tools/capture_template.py iron_sword --threshold 0.82 --name "Iron Sword"
```

By default, the tool waits for `Shift+C`, takes a screenshot, then opens a selector where you draw a box and press Enter/Space to confirm.

If you prefer the old cursor-centered square capture mode:

```bash
python tools/capture_template.py iron_sword --mode cursor --countdown 3 --size 56 --threshold 0.82 --name "Iron Sword"
```

The tool saves `assets/templates/iron_sword.png` and prints a JSON snippet to paste into `data/items.json`.

## Tuning tips

- Start with 15-30 templates for near real-time response.
- If false positives occur, increase threshold for specific items.
- If misses occur due to scale differences, keep item icon size stable and add extra templates for that item.
- ROI size (`--roi-radius`) is the biggest speed/accuracy tradeoff.

## Key files

- `main.py` - app entry point
- `overlay_app/controller.py` - hotkey to capture/match/render orchestration
- `overlay_app/template_matcher.py` - template matching engine
- `overlay_app/overlay_window.py` - transparent overlay rendering
- `overlay_app/item_repository.py` - JSON item database loader
- `tools/capture_template.py` - template capture helper

## Architecture documentation

- `docs/ARCHITECTURE.md` - system design, module responsibilities, runtime flow, and extension points

## Known limitations

- Template matching can confuse visually similar icons.
- Exclusive fullscreen and anti-cheat protections may block capture/overlay behavior.
- Very large template libraries may increase CPU usage and latency.
