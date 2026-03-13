"""
Bazaar Overlay - OCR-based item info overlay for games.

Usage:
    python main.py              # Normal mode
    python main.py --debug      # Debug mode (shows OCR region)

Hold Shift+E over an item in the game to see its info.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from overlay_app.config import AppConfig, CaptureConfig, OcrConfig
from overlay_app.controller import AppController
from overlay_app.item_repository import ItemRepository
from overlay_app.overlay_window import DebugOverlayWindow, OverlayWindow
from overlay_app.screen_capture import enable_dpi_awareness


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    default_items = Path(__file__).resolve().parent / "data" / "items.json"
    parser = argparse.ArgumentParser(
        description="Display item info overlay using OCR while holding Shift+E."
    )
    parser.add_argument(
        "--items",
        type=Path,
        default=default_items,
        help="Path to item manifest JSON file.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode showing OCR region.",
    )
    parser.add_argument(
        "--roi-radius",
        type=int,
        default=400,
        help="Capture radius around cursor in pixels.",
    )
    parser.add_argument(
        "--skip-frames",
        type=int,
        default=1,
        help="Skip OCR every N frames (1 = no skip, 2 = half speed, etc).",
    )
    parser.add_argument(
        "--poll-ms",
        type=int,
        default=75,
        help="Detection loop interval while hotkey is held.",
    )
    parser.add_argument(
        "--ocr-region",
        type=str,
        default="0,0,0,0",
        help="OCR region as 'x,y,width,height' (0,0,0,0 = full ROI).",
    )
    return parser.parse_args()


def configure_logging(debug: bool) -> None:
    """Configure logging based on debug flag."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_config(args: argparse.Namespace) -> AppConfig:
    """Build app configuration from parsed arguments."""
    capture = CaptureConfig(
        roi_radius=max(24, int(args.roi_radius)),
        poll_interval_ms=max(25, int(args.poll_ms)),
        skip_frames=max(1, int(args.skip_frames)),
    )
    
    # Parse OCR region: "x,y,width,height"
    ocr_region = args.ocr_region.split(",")
    if len(ocr_region) == 4:
        ocr_x, ocr_y, ocr_w, ocr_h = map(int, ocr_region)
    else:
        ocr_x, ocr_y, ocr_w, ocr_h = 0, 0, 0, 0
    
    ocr = OcrConfig(
        enabled=True,  # OCR is always enabled
        region_x=ocr_x,
        region_y=ocr_y,
        region_width=ocr_w,
        region_height=ocr_h,
    )
    
    return AppConfig(
        items_path=args.items.resolve(),
        debug=bool(args.debug),
        capture=capture,
        ocr=ocr,
    )


def main() -> int:
    """Main entry point."""
    args = parse_args()
    configure_logging(debug=bool(args.debug))

    # Enable DPI awareness for accurate screen coordinates
    enable_dpi_awareness()
    config = build_config(args)
    
    # Load item definitions from JSON
    repository = ItemRepository()
    try:
        items = repository.load_items(config.items_path)
    except Exception as exc:
        logging.getLogger("overlay.main").error("Failed to load item database: %s", exc)
        return 1

    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Create overlay windows
    overlay = OverlayWindow(config.overlay)
    debug_overlay = DebugOverlayWindow() if config.debug else None
    
    # Create and start controller
    controller = AppController(
        config=config, 
        items=items, 
        overlay=overlay, 
        debug_overlay=debug_overlay
    )
    controller.start()
    app.aboutToQuit.connect(controller.shutdown)

    logging.getLogger("overlay.main").info(
        "Running. Hold Shift+E over an item to show overlay."
    )
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
