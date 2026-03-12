from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from overlay_app.config import AppConfig, CaptureConfig, MatchConfig, OcrConfig
from overlay_app.controller import AppController
from overlay_app.item_repository import ItemRepository
from overlay_app.overlay_window import OverlayWindow
from overlay_app.screen_capture import enable_dpi_awareness


def parse_args() -> argparse.Namespace:
    default_items = Path(__file__).resolve().parent / "data" / "items.json"
    parser = argparse.ArgumentParser(
        description="Display template-matched item info overlay while holding Shift+E."
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
        help="Enable verbose logs and timing in overlay.",
    )
    parser.add_argument(
        "--roi-radius",
        type=int,
        default=72,
        help="Capture radius around cursor in pixels.",
    )
    parser.add_argument(
        "--poll-ms",
        type=int,
        default=75,
        help="Detection loop interval while hotkey is held.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Global fallback confidence threshold (0-1).",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Use OCR-based detection instead of template matching.",
    )
    parser.add_argument(
        "--ocr-region",
        type=str,
        default="0,0,200,50",
        help="OCR region as 'x,y,width,height' relative to cursor.",
    )
    return parser.parse_args()


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_config(args: argparse.Namespace) -> AppConfig:
    capture = CaptureConfig(
        roi_radius=max(24, int(args.roi_radius)),
        poll_interval_ms=max(25, int(args.poll_ms)),
    )
    
    ocr_region = args.ocr_region.split(",")
    if len(ocr_region) == 4:
        ocr_x, ocr_y, ocr_w, ocr_h = map(int, ocr_region)
    else:
        ocr_x, ocr_y, ocr_w, ocr_h = 0, 0, 200, 50
    
    ocr = OcrConfig(
        enabled=bool(args.ocr),
        region_x=ocr_x,
        region_y=ocr_y,
        region_width=ocr_w,
        region_height=ocr_h,
    )
    
    matching = MatchConfig(global_threshold=max(0.05, min(0.99, float(args.threshold))))
    return AppConfig(
        items_path=args.items.resolve(),
        debug=bool(args.debug),
        capture=capture,
        ocr=ocr,
        matching=matching,
    )


def main() -> int:
    args = parse_args()
    configure_logging(debug=bool(args.debug))

    enable_dpi_awareness()
    config = build_config(args)
    repository = ItemRepository()

    try:
        items = repository.load_items(config.items_path)
    except Exception as exc:  # pragma: no cover - startup path
        logging.getLogger("overlay.main").error("Failed to load item database: %s", exc)
        return 1

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    overlay = OverlayWindow(config.overlay)
    controller = AppController(config=config, items=items, overlay=overlay)
    controller.start()
    app.aboutToQuit.connect(controller.shutdown)

    mode = "OCR" if config.ocr.enabled else "Template Matching"
    logging.getLogger("overlay.main").info(
        "Running in %s mode. Hold Shift+E over an item to show overlay.", mode
    )
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
