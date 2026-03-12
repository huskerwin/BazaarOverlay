# Architecture

This document describes how the Bazaar Overlay MVP is structured and how data moves through the app while `Shift+E` is held.

## Goals and constraints

- Keep detection near real-time for a small-to-medium template database.
- Render a lightweight, non-intrusive overlay near the cursor.
- Stay read-only with respect to the game: only screen capture and local display.
- Keep code modular so matching logic, capture backend, and UI can evolve independently.

## High-level flow

1. User holds `Shift+E`.
2. Global hotkey listener reports `active=True` to controller.
3. Worker loop captures a cursor-centered ROI from desktop.
4. Matcher runs a hybrid pass: template shortlist, ORB re-ranking, and final confidence scoring.
5. Controller applies short temporal smoothing/stability checks to reduce one-frame mislabels.
6. Controller builds an overlay payload (matched item or fallback message).
7. UI thread renders overlay near cursor.
8. User releases `Shift+E` and overlay hides immediately.

## Module map

- `main.py`
  - Application entrypoint.
  - Parses CLI flags and builds runtime config.
  - Loads item definitions and wires controller + overlay window.

- `overlay_app/config.py`
  - Dataclasses for capture, matching, overlay, and app-wide config.

- `overlay_app/item_repository.py`
  - Loads `data/items.json`.
  - Validates and normalizes item records.
  - Resolves template paths and per-item thresholds.

- `overlay_app/hotkey_listener.py`
  - Global key-state listener using `pynput`.
  - Emits hold-state transitions for `Shift+E`.

- `overlay_app/screen_capture.py`
  - Enables DPI awareness.
  - Captures a bounded region around current cursor via `mss`.

- `overlay_app/template_matcher.py`
  - Preloads templates into multi-scale variants.
  - Computes grayscale/edge template scores, builds a top-N shortlist, and re-ranks with ORB feature matching.
  - Applies a center-bias term so matches near cursor/ROI center are favored over corner matches.
  - Produces a thresholded match decision with blended confidence.

- `overlay_app/ocr_detector.py`
  - OCR-based item detection using EasyOCR.
  - Reads text from a configurable region around the cursor.
  - Matches extracted text against known item names from the item database.
  - Faster than template matching for large item databases.

- `overlay_app/controller.py`
  - Orchestrates hotkey, capture, match, and overlay updates.
  - Applies temporal smoothing and a minimum stable-frame requirement before showing a positive match.
  - Runs detection in a worker thread while hotkey is active.
  - Emits Qt signals so rendering stays on the UI thread.

- `overlay_app/overlay_window.py`
  - Transparent, always-on-top, click-through Qt window.
  - Draws title/body/confidence and clamps position to screen bounds.

- `tools/capture_template.py`
  - Utility for capturing template images in either `hotkey-box` mode (`Shift+C` + draw box) or cursor mode.
  - Prints a manifest snippet to speed up item DB expansion.

- `Run Bazaar Overlay.cmd` / `Run Capture Template.cmd`
  - Windows launcher scripts for one-click execution.

- `tools/create_shortcut.ps1`
  - Creates desktop shortcuts for both launcher scripts.

## Runtime architecture

### Threading model

- Main thread: Qt event loop, window creation, and all painting.
- Worker thread (`item-detection-loop`): capture + match cycle.
- `pynput` listener thread: keyboard callbacks.

The controller uses an event gate (`threading.Event`) to run detection only while the hotkey is active. UI updates are emitted as Qt signals to avoid cross-thread widget access.

### Detection loop details

The controller supports two detection modes:

#### Template Matching Mode (default)

1. Capture ROI around cursor (`roi_radius` from config).
2. Convert ROI to normalized grayscale and edges.
3. Score every template variant with `cv2.matchTemplate` and keep best score per item.
4. Shortlist the top candidate items by template score.
5. Re-rank shortlist with ORB descriptor matching and blend scores.
6. Apply temporal smoothing and stability gating in controller.
7. Compare smoothed score against per-item threshold or global fallback.
8. Emit overlay payload with text and confidence.
9. Sleep to maintain configured polling interval.

#### OCR Mode (alternative)

When `--ocr` flag is enabled:
1. Capture ROI around cursor.
2. Extract text from configured region using EasyOCR.
3. Match extracted text against item names from the database.
4. Apply temporal smoothing for stability.
5. Emit overlay payload with matched item info.

OCR mode is typically faster for large template databases but requires the game to display item names in a consistent location.

## Data model

- Manifest path: `data/items.json`
- Item fields:
  - `enabled` (optional; `false` skips the item without deleting it)
  - `id` (optional; generated from name if omitted)
  - `name` (required)
  - `template` (single path) and/or `templates` (list of paths)
  - `threshold` (optional, item-specific)
  - `info` (optional overlay body text)

Templates are loaded at startup and expanded into scale variants (default: `0.90`, `1.00`, `1.10`).

## Why this architecture

- Responsiveness: matching is isolated from UI rendering, so overlays stay smooth.
- Debuggability: each concern has a dedicated module and explicit interfaces.
- Extensibility: capture backend, matcher strategy, and overlay style can change independently.
- Safety: no game memory access or input automation.

## Extension points

- Capture backends
  - Swap `mss` for `dxcam` while keeping `ScreenCapture` API stable.

- Matching strategies
  - Add ORB/SIFT or feature-based fallback for highly similar icons.
  - Add coarse-to-fine indexing for larger template libraries.

- Window scoping
  - Restrict detection to a target game window title/process.

- Caching and performance
  - Add ROI temporal caching and candidate narrowing across frames.

- Developer tooling
  - Add debug window to preview ROI and top-N match scores live.

## Performance considerations

- Biggest levers:
  - ROI size (`--roi-radius`)
  - Poll interval (`--poll-ms`)
  - Number of templates and scale variants

- ROI guardrail:
  - The controller auto-raises ROI radius when configured value is smaller than the largest loaded template.

- Current tradeoff:
  - Better robustness from multi-scale + edge scoring at modest CPU cost.

- Recommended starting point:
  - 15-30 templates, `roi_radius=72`, `poll_ms=75`, tune thresholds by item.

## Failure modes and behavior

- Template files missing or unreadable
  - Repository logs warnings and skips invalid entries.
  - Startup fails if no valid templates remain.

- No confident match
  - Overlay shows `No confident match found.` and best candidate when available.

- Runtime capture/match error
  - Controller logs exception and shows a visible error payload.

## Resolution and scaling strategy

- DPI awareness is enabled on startup to align cursor, capture, and overlay coordinates.
- Template scaling variants absorb mild UI scaling differences.
- For major UI changes, capture additional templates per item at those settings.

## Security and compliance boundary

- Allowed: screen capture, local template matching, local overlay rendering.
- Not allowed: gameplay automation, synthetic in-game actions, or memory manipulation.
