# Developer Guide - Bazaar Overlay

This guide explains how the Bazaar Overlay application works, from a developer's perspective.

## Overview

Bazaar Overlay is an OCR-based tool that displays item information when you hold `Shift+E` over items in a game. It captures the screen, uses OCR to read text, matches against a database, and shows an overlay with item details.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Application                        │
│  (main.py - entry point, parses args, creates Qt app)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   AppController                               │
│  - Orchestrates everything                                  │
│  - Runs detection loop in worker thread                    │
│  - Manages hotkey state                                    │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐  ┌─────────┐  ┌──────────┐
   │ Hotkey  │   │  Screen  │  │   OCR   │  │ Overlay │
   │Listener │   │ Capture  │  │Detector │  │ Window  │
   └─────────┘   └──────────┘  └─────────┘  └──────────┘
```

## Core Components

### 1. main.py - Entry Point

**Purpose**: Application entry point that:
- Parses command-line arguments
- Creates the Qt application
- Wires together all components
- Starts the controller

**Key functions**:
- `parse_args()` - Handles CLI arguments (--debug, --roi-radius, --skip-frames, etc.)
- `build_config()` - Creates AppConfig from arguments
- `main()` - Creates Qt app, loads items, starts controller

### 2. controller.py - AppController

**Purpose**: Main orchestrator that coordinates all components

**Key responsibilities**:
- Manages the detection loop (worker thread)
- Handles hotkey state (Shift+E press/release)
- Calls OCR detection
- Builds overlay payloads
- Shows/hides overlay windows

**Detection Loop**:
```python
while hotkey_is_pressed:
    1. Capture screen around cursor
    2. Run OCR detection
    3. Apply stability check (need 2 consecutive matches)
    4. Build overlay with item info
    5. Show overlay (in top-right of screen)
    6. Sleep for poll_interval_ms
```

**Key methods**:
- `start()` - Starts worker thread and hotkey listener
- `shutdown()` - Stops everything cleanly
- `_worker_loop()` - Main detection loop
- `_detect()` - Runs OCR on captured screen
- `_stabilize_result()` - Requires 2 consecutive matches to avoid flicker
- `_build_overlay_payload()` - Creates data for overlay display

### 3. ocr_detector.py - OcrItemDetector

**Purpose**: Uses EasyOCR to read text from screen captures

**How it works**:
1. Crop the image to OCR region (or full ROI)
2. Run EasyOCR to extract text
3. Clean and normalize the text
4. Match against known item names using fuzzy matching

**Matching strategies** (in order):
1. Exact match (case-insensitive)
2. Contains match (item name in OCR text or vice versa)
3. Apostrophe-insensitive (e.g., "Dragons Breath" matches "Dragon's Breath")
4. Fuzzy normalized (handles plurals, slight OCR errors)

**Key methods**:
- `detect_from_image(frame, region)` - Main detection method
- `_clean_text()` - Normalizes OCR output
- `_find_best_match()` - Matches against item database

### 4. screen_capture.py - ScreenCapture

**Purpose**: Captures a region of the screen around the cursor

**How it works**:
- Uses `mss` library for fast screen capture
- Captures a square region around cursor (size = roi_radius * 2)
- Returns BGR image, cursor position, and capture region

**Key methods**:
- `capture_around_cursor()` - Returns (image, cursor_pos, region)

### 5. hotkey_listener.py - HoldHotkeyListener

**Purpose**: Listens for keyboard input

**How it works**:
- Uses `pynput` library
- Tracks Shift + E key combination
- Calls callback when state changes (pressed/released)

**Key methods**:
- `start()` - Starts keyboard listener
- `stop()` - Stops listener
- `_on_press()` / `_on_release()` - Handles key events

### 6. overlay_window.py - OverlayWindow

**Purpose**: Displays the info overlay

**How it works**:
- Transparent, always-on-top Qt window
- Click-through (doesn't intercept mouse clicks)
- Positioned in top-right of screen

**Key methods**:
- `show_payload()` - Updates and shows overlay
- `hide_overlay()` - Hides overlay
- `paintEvent()` - Draws the overlay UI
- `_move_near_cursor()` - Positions window

**DebugOverlayWindow**: 
- Shows captured screen region for debugging
- Displays red rectangle where OCR is running

### 7. item_repository.py - ItemRepository

**Purpose**: Loads item definitions from JSON

**How it works**:
- Reads `data/items.json`
- Validates and parses item entries
- Returns list of ItemDefinition objects

**Item format**:
```json
{
  "items": [
    {
      "id": "unique_id",
      "name": "Item Name",
      "info": "Description shown in overlay",
      "enabled": true
    }
  ]
}
```

### 8. config.py - Configuration

**Purpose**: Defines all configuration dataclasses

**Key configs**:
- `CaptureConfig` - Screen capture settings (roi_radius, poll_interval_ms, skip_frames)
- `OcrConfig` - OCR settings (region_x, region_y, region_width, region_height)
- `OverlayConfig` - Overlay display settings (width, height, position)
- `AppConfig` - Combined app configuration

### 9. models.py - Data Classes

**Purpose**: Defines data structures

**Key classes**:
- `ItemDefinition` - Item from database (id, name, info)
- `MatchResult` - OCR detection result (matched, confidence, item, message)
- `OverlayPayload` - Data passed to overlay (title, body, cursor_pos, etc.)
- `OcrRegion` - OCR region definition (left, top, width, height)

## Configuration Options

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|--------------|
| `--debug` | false | Enable debug mode (shows OCR region) |
| `--roi-radius` | 400 | Capture radius around cursor (pixels) |
| `--poll-ms` | 75 | Detection loop interval (milliseconds) |
| `--skip-frames` | 1 | Skip OCR every N frames (1=no skip) |
| `--ocr-region` | 0,0,0,0 | OCR region (x,y,width,height), 0=full ROI |
| `--items` | data/items.json | Path to items database |

### How OCR Region Works

The OCR region is relative to the captured ROI:
- ROI is captured at `cursor_pos ± roi_radius`
- OCR region is relative to ROI top-left corner
- Use `0,0,0,0` to scan the entire ROI

Example: To scan 200x40 region starting 100px right of cursor with roi_radius=400:
- ROI top-left = cursor - 400
- Want region at cursor + 100
- So: ROI_left + x = cursor + 100
- cursor - 400 + x = cursor + 100
- x = 500

## Performance Tips

1. **Smaller ROI radius** = Faster OCR
   - Default 400 captures 800x800 pixels
   - Try 200 for 400x400 (4x faster)

2. **Skip frames** = Skip OCR on alternate frames
   - `--skip-frames 2` runs OCR every other cycle
   - Shows last known result in between

3. **Smaller OCR region** = Faster
   - Instead of full ROI, specify a smaller region
   - Only scans where item names typically appear

## Threading Model

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Main Thread   │     │  Worker Thread   │     │ pynput     │
│                 │     │                  │     │  Thread     │
│ - Qt Event Loop │     │ - Detection Loop │     │             │
│ - UI Rendering  │◄────│ - OCR Detection  │     │ - Keyboard  │
│ - Window Mgmt   │     │ - Capture       │     │   Events    │
└─────────────────┘     └──────────────────┘     └─────────────┘
        │                        │
        │ Qt Signals            │ No direct calls
        ▼                        ▼
  ┌─────────────────────────────────────┐
  │        AppController                 │
  │  - Coordinates everything            │
  │  - Uses events for thread safety    │
  └─────────────────────────────────────┘
```

**Key points**:
- Worker thread runs detection loop
- UI updates via Qt signals (thread-safe)
- Hotkey callbacks come from pynput thread
- Screen capture is thread-local (mss sessions)

## Debug Mode

When `--debug` is enabled:
1. DebugOverlayWindow shows captured screen
2. Red rectangle shows OCR region
3. Processing time displayed in overlay
4. Console shows OCR detection logs

Useful for:
- Finding the right OCR region
- Understanding what OCR is reading
- Troubleshooting detection issues

## Extension Points

Want to modify the app? Here are the key areas:

### Add new detection method
1. Create new detector class (like OcrItemDetector)
2. Modify `controller.py::_detect()` to use it
3. Update config if needed

### Change overlay appearance
1. Edit `overlay_window.py::paintEvent()`
2. Modify colors, fonts, layout
3. Update OverlayConfig for size changes

### Add new hotkey
1. Modify `hotkey_listener.py::trigger_key`
2. Or add more keys to track

### Change item database
1. Edit `data/items.json`
2. Or modify `item_repository.py` to load from different source
