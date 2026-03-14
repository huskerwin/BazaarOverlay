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

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from overlay_app.config import AppConfig, CaptureConfig, OcrConfig, OverlayConfig
from overlay_app.controller import AppController
from overlay_app.item_repository import ItemRepository
from overlay_app.overlay_window import DebugOverlayWindow, OverlayWindow
from overlay_app.screen_capture import enable_dpi_awareness
from overlay_app.settings_manager import SettingsManager
from overlay_app.settings_window import SettingsWindow


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
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
        "--roi-width",
        type=int,
        help="Capture width around cursor in pixels.",
    )
    parser.add_argument(
        "--roi-height",
        type=int,
        help="Capture height around cursor in pixels.",
    )
    parser.add_argument(
        "--skip-frames",
        type=int,
        help="Skip OCR every N frames (1 = no skip, 2 = half speed, etc).",
    )
    parser.add_argument(
        "--poll-ms",
        type=int,
        help="Detection loop interval while hotkey is held.",
    )
    parser.add_argument(
        "--ocr-region",
        type=str,
        help="OCR region as 'x,y,width,height' (0,0,0,0 = full ROI).",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Disable system tray icon.",
    )
    return parser.parse_args(args)


def configure_logging(debug: bool) -> None:
    """Configure logging based on debug flag."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_config(args: argparse.Namespace, settings: SettingsManager) -> AppConfig:
    """Build app configuration from parsed arguments and settings."""
    # Get values from args, fall back to settings
    s = settings.get_all()
    
    roi_width = args.roi_width if args.roi_width is not None else s.get("roi_width", 1200)
    roi_height = args.roi_height if args.roi_height is not None else s.get("roi_height", 800)
    poll_ms = args.poll_ms if args.poll_ms is not None else s.get("poll_ms", 75)
    skip_frames = args.skip_frames if args.skip_frames is not None else s.get("skip_frames", 7)
    debug = args.debug if args.debug else s.get("debug", False)
    ocr_region_str = args.ocr_region if args.ocr_region is not None else s.get("ocr_region", "0,0,0,0")
    
    capture = CaptureConfig(
        roi_width=max(24, int(roi_width)),
        roi_height=max(24, int(roi_height)),
        poll_interval_ms=max(25, int(poll_ms)),
        skip_frames=max(1, int(skip_frames)),
    )
    
    # Parse OCR region: "x,y,width,height"
    ocr_region = ocr_region_str.split(",")
    if len(ocr_region) == 4:
        ocr_x, ocr_y, ocr_w, ocr_h = map(int, ocr_region)
    else:
        ocr_x, ocr_y, ocr_w, ocr_h = 0, 0, 0, 0
    
    ocr = OcrConfig(
        enabled=True,
        region_x=ocr_x,
        region_y=ocr_y,
        region_width=ocr_w,
        region_height=ocr_h,
    )
    
    return AppConfig(
        items_path=args.items.resolve(),
        debug=bool(debug),
        capture=capture,
        ocr=ocr,
    )


class BazaarOverlayApp:
    """Main application class with system tray integration."""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.logger = logging.getLogger("overlay.main")
        self._settings = SettingsManager()
        self._config = build_config(args, self._settings)
        self._controller: AppController | None = None
        self._tray_icon: QSystemTrayIcon | None = None
        self._app: QApplication | None = None
    
    def _get_asset_path(self, filename: str) -> Path:
        """Get path to asset, works both in dev and packaged exe."""
        if getattr(sys, 'frozen', False):
            # Running as packaged exe
            base_path = Path(sys._MEIPASS)
        else:
            # Running in development
            base_path = Path(__file__).parent
        return base_path / "assets" / filename
    
    def run(self) -> int:
        """Run the application."""
        configure_logging(debug=self._config.debug)
        
        # Enable DPI awareness
        enable_dpi_awareness()
        
        # Create Qt application
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        
        # Check if first run (before SettingsManager creates the file)
        import os
        app_data = Path(os.environ.get("APPDATA", ""))
        config_dir = app_data / "BazaarOverlay"
        config_file = config_dir / "settings.json"
        is_first_run = not config_file.exists()
        
        # Load items
        repository = ItemRepository()
        try:
            items = repository.load_items(self._config.items_path)
        except Exception as exc:
            self.logger.error("Failed to load item database: %s", exc)
            return 1
        
        # Create overlay windows
        overlay = OverlayWindow(self._config.overlay)
        debug_overlay = DebugOverlayWindow() if self._config.debug else None
        
        # Create controller
        self._controller = AppController(
            config=self._config,
            items=items,
            overlay=overlay,
            debug_overlay=debug_overlay
        )
        
        # Setup system tray
        if not args.no_tray:
            self._setup_tray()
        
        # Show settings on first startup
        if is_first_run:
            self._show_settings()
        
        # Start controller
        self._controller.start()
        self._app.aboutToQuit.connect(self._shutdown)
        
        self.logger.info("Running. Hold Shift+E over an item to show overlay.")
        return self._app.exec()
    
    def _setup_tray(self) -> None:
        """Setup system tray icon and menu."""
        self._tray_icon = QSystemTrayIcon()
        
        # Try to load icon, fallback to default
        icon_path = self._get_asset_path("icon.ico")
        if icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            icon_path_png = self._get_asset_path("icon.png")
            if icon_path_png.exists():
                self._tray_icon.setIcon(QIcon(str(icon_path_png)))
            else:
                self._tray_icon.setIcon(self._app.style().standardIcon(
                    self._app.style().StandardPixmap.SP_ComputerIcon
                ))
        
        self._tray_icon.setToolTip("Bazaar Overlay\nHold Shift+E over items")
        
        # Create tray menu (keep reference to prevent garbage collection)
        self._tray_menu = QMenu()
        
        self._status_action = QAction("Status: Running")
        self._status_action.setEnabled(False)
        self._tray_menu.addAction(self._status_action)
        
        self._tray_menu.addSeparator()
        
        settings_action = QAction("Settings...")
        settings_action.triggered.connect(self._show_settings)
        self._tray_menu.addAction(settings_action)
        
        self._tray_menu.addSeparator()
        
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self._quit)
        self._tray_menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(self._tray_menu)
        self._tray_icon.activated.connect(self._tray_activated)
        self._tray_icon.show()
    
    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_settings()
    
    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsWindow(self._settings)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.quit_app.connect(self._quit)
        dialog.exec()
    
    def _on_settings_changed(self, new_settings: dict) -> None:
        """Handle settings changes - restart controller with new config."""
        self.logger.info("Settings changed, restarting...")
        
        # Stop controller
        if self._controller:
            self._controller.shutdown()
        
        # Rebuild config with new settings
        self._config = build_config(self.args, self._settings)
        
        # Reload items
        repository = ItemRepository()
        try:
            items = repository.load_items(self._config.items_path)
        except Exception as exc:
            self.logger.error("Failed to reload item database: %s", exc)
            return
        
        # Recreate overlay windows
        overlay = OverlayWindow(self._config.overlay)
        debug_overlay = DebugOverlayWindow() if self._config.debug else None
        
        # Recreate controller
        self._controller = AppController(
            config=self._config,
            items=items,
            overlay=overlay,
            debug_overlay=debug_overlay
        )
        self._controller.start()
        
        self.logger.info("Restarted with new settings")
    
    def _shutdown(self) -> None:
        """Shutdown application cleanly."""
        if self._controller:
            self._controller.shutdown()
    
    def _quit(self) -> None:
        """Quit the application."""
        self._shutdown()
        self._app.quit()


def main() -> int:
    """Main entry point."""
    global args
    args = parse_args()
    
    app = BazaarOverlayApp(args)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
