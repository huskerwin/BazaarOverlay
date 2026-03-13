# Architecture

This document describes how the Bazaar Overlay works - an OCR-based item info overlay that displays information when holding `Shift+E` over items in a game.

## Goals and constraints

- Keep detection fast using OCR instead of template matching.
- Render a lightweight, non-intrusive overlay near the cursor.
- Stay read-only with respect to the game: only screen capture and local display.
- Keep code modular so OCR logic, capture backend, and UI can evolve independently.

## High-level flow

1. User holds `Shift+E`.
2. Global hotkey listener reports `active=True` to controller.
3. Worker loop captures a cursor-centered ROI from desktop.
4. OCR detector extracts text from a configurable region.
5. Extracted text is matched against known item names.
6. Controller applies brief stability check (2 frames) before showing a match.
7. Controller builds an overlay payload (matched item or detected text).
8. UI thread renders overlay near cursor.
9. User releases `Shift+E` and overlay hides immediately.

## Module map

### Core Application

- `main.py`
  - Application entry point.
  - Parses CLI flags and builds runtime config.
  - Loads item definitions and wires controller + overlay window.

- `overlay_app/config.py`
  - Dataclasses for capture, OCR, and overlay configuration.

- `overlay_app/item_repository.py`
  - Loads `data/items.json`.
  - Validates and normalizes item records.
  - Extracts item name and info for OCR matching.

- `overlay_app/models.py`
  - Data classes: `ItemDefinition`, `MatchResult`, `OverlayPayload`, `OcrRegion`.

### Detection

- `overlay_app/hotkey_listener.py`
  - Global key-state listener using `pynput`.
  - Emits hold-state transitions for `Shift+E`.

- `overlay_app/screen_capture.py`
  - Enables DPI awareness for accurate screen coordinates.
  - Captures a bounded region around current cursor via `mss`.

- `overlay_app/ocr_detector.py`
  - OCR-based item detection using EasyOCR.
  - Extracts text from a configurable region relative to cursor.
  - Matches extracted text against known item names using fuzzy matching.
  - Handles apostrophes, case insensitivity, and partial matches.

- `overlay_app/controller.py`
  - Orchestrates hotkey, capture, OCR detection, and overlay updates.
  - Applies stability check (requires 2 consecutive matches) before showing positive match.
  - Runs detection in a worker thread while hotkey is active.
  - Emits Qt signals so rendering stays on the UI thread.

### UI

- `overlay_app/overlay_window.py`
  - Transparent, always-on-top, click-through Qt window.
  - Draws title, body, and confidence text.
  - Clamps position to screen bounds.
  - Includes debug overlay window for visualizing OCR region (when `--debug` enabled).

### Tools

- `tools/capture_template.py`
  - Utility for capturing template images (legacy - not used in OCR mode).

- `Run Bazaar Overlay.cmd`
  - Windows launcher script for one-click execution with debug mode.

## Runtime architecture

### Threading model

- Main thread: Qt event loop, window creation, and all painting.
- Worker thread (`item-detection-loop`): capture + OCR detection cycle.
- `pynput` listener thread: keyboard callbacks.

The controller uses an event gate (`threading.Event`) to run detection only while the hotkey is active. UI updates are emitted as Qt signals to avoid cross-thread widget access.

### Detection loop details (OCR Mode)

1. Capture ROI around cursor (`roi_radius` from config).
2. Crop OCR region from ROI based on configured offset (x, y) and size (width, height).
3. Run EasyOCR on cropped region to extract text.
4. Clean and normalize extracted text.
5. Match against item names from database using fuzzy matching.
6. Apply stability check (2 consecutive matches required).
7. Emit overlay payload with matched item or detected text.
8. Sleep to maintain configured polling interval.

## Configuration

### CLI Flags

- `--debug`: Enable debug mode showing OCR region visualization
- `--roi-radius`: Capture radius around cursor in pixels (default: 400)
- `--poll-ms`: Detection loop interval in milliseconds (default: 75)
- `--ocr-region`: OCR region as 'x,y,width,height' relative to cursor (default: "500,-50,200,40")
- `--items`: Path to item manifest JSON file

### OCR Region

The OCR region is defined relative to the cursor position:
- `x`: Pixels to the right of cursor (positive) or left (negative)
- `y`: Pixels below cursor (positive) or above (negative)
- `width`: Width of OCR capture region
- `height`: Height of OCR capture region

Example: `500,-50,200,40` means 500px right, 50px above, 200px wide, 40px tall.

## Data model

- Manifest path: `data/items.json`
- Item fields:
  - `enabled` (optional; `false` skips the item)
  - `id` (optional; generated from name if omitted)
  - `name` (required - this is what OCR matches against)
  - `info` (optional overlay body text)

## Why this architecture

- Responsiveness: OCR detection is isolated from UI rendering, so overlays stay smooth.
- Debuggability: each concern has a dedicated module and explicit interfaces.
- Extensibility: capture backend, OCR strategy, and overlay style can change independently.
- Safety: no game memory access or input automation.

## Performance considerations

- Biggest levers:
  - ROI size (`--roi-radius`) - larger = more context but slower
  - Poll interval (`--poll-ms`) - lower = more responsive but more CPU
  - OCR region size - smaller = faster OCR

- Current tradeoff:
  - OCR is fast but EasyOCR model loads on startup (first detection takes longer)
  - Debug mode shows processing time in overlay

## Failure modes and behavior

- No text detected
  - Overlay shows "Move cursor over an item name in the game."

- Text detected but no match
  - Overlay shows "Detected: 'text'" so user can see what OCR read.

- OCR region outside captured area
  - Increase `--roi-radius` to capture more of the screen.

- Runtime capture/OCR error
  - Controller logs exception and shows visible error payload.

## Security and compliance boundary

- Allowed: screen capture, OCR text extraction, local overlay rendering.
- Not allowed: gameplay automation, synthetic in-game actions, or memory manipulation.
