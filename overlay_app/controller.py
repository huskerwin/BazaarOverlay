"""
Application controller.

Orchestrates hotkey detection, screen capture, OCR detection, and overlay rendering.
Runs detection in a worker thread while hotkey is active.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TypedDict

import cv2
import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from .config import AppConfig
from .hotkey_listener import HoldHotkeyListener
from .models import ItemDefinition, MatchResult, OverlayPayload, OcrRegion
from .ocr_detector import OcrItemDetector
from .overlay_window import OverlayWindow
from .screen_capture import ScreenCapture

LOGGER = logging.getLogger("overlay.controller")


class AppController(QObject):
    """
    Main application controller.
    
    Coordinates hotkey detection, screen capture, OCR detection, and overlay updates.
    Uses Qt signals for thread-safe UI updates.
    """
    
    # Qt signals for UI updates
    overlay_show = Signal(object)
    overlay_hide = Signal()

    def __init__(
        self, 
        config: AppConfig, 
        items: list[ItemDefinition], 
        overlay: OverlayWindow,
        debug_overlay=None
    ):
        """
        Initialize controller.
        
        Args:
            config: Application configuration
            items: List of item definitions
            overlay: Main overlay window
            debug_overlay: Optional debug overlay window
        """
        super().__init__()
        self._config = config

        # Stability tracking - require 2 consecutive matches
        self._last_item_name: str | None = None
        self._item_streak = 0

        self._overlay = overlay
        self._debug_overlay = debug_overlay
        self._debug_shown_this_activation = False
        self._last_result: tuple[MatchResult, tuple[int, int]] | None = None
        
        # Initialize screen capture
        self._capture = ScreenCapture(config.capture.roi_radius)
        
        # Initialize OCR detector with known item names
        item_names = {item.name for item in items}
        LOGGER.info("Initializing OCR detector...")
        self._ocr_detector = OcrItemDetector(item_names)
        
        # Configure OCR region
        self._ocr_region: OcrRegion = {
            "left": config.ocr.region_x,
            "top": config.ocr.region_y,
            "width": config.ocr.region_width,
            "height": config.ocr.region_height,
        }
        LOGGER.info("OCR detection enabled with region: %s", self._ocr_region)

        # Start hotkey listener
        self._hotkey = HoldHotkeyListener(
            on_state_change=self._on_hotkey_state, 
            trigger_key="e"
        )
        
        # Build item lookup by name
        self._items_by_name: dict[str, ItemDefinition] = {
            item.name: item for item in items
        }

        # Threading
        self._state_lock = threading.Lock()
        self._active = False
        self._active_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="item-detection-loop",
            daemon=True,
        )

        # Connect Qt signals
        self.overlay_show.connect(self._overlay.show_payload)
        self.overlay_hide.connect(self._overlay.hide_overlay)

    def start(self) -> None:
        """Start the controller (hotkey listener and worker thread)."""
        self._worker_thread.start()
        self._hotkey.start()

    def shutdown(self) -> None:
        """Stop the controller and clean up resources."""
        self._hotkey.stop()
        self._active_event.clear()
        self._reset_temporal_state()
        self._shutdown_event.set()
        self.overlay_hide.emit()

        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

    def _on_hotkey_state(self, active: bool) -> None:
        """
        Handle hotkey state changes.
        
        Called from hotkey listener thread.
        """
        with self._state_lock:
            if active == self._active:
                return
            self._active = active

        if active:
            self._active_event.set()
        else:
            self._active_event.clear()
            self._reset_temporal_state()
            self.overlay_hide.emit()
            # Hide debug overlay using Qt timer for thread safety
            if self._debug_overlay is not None:
                QTimer.singleShot(0, self._debug_overlay.hide_debug)

    def _worker_loop(self) -> None:
        """
        Main detection loop.
        
        Runs in separate thread while hotkey is active.
        """
        poll_seconds = self._config.capture.poll_interval_ms / 1000.0
        frame_count = 0

        while not self._shutdown_event.is_set():
            # Wait for hotkey activation
            if not self._active_event.wait(timeout=0.10):
                continue

            # Reset debug flag and frame count at start of new activation
            self._debug_shown_this_activation = False
            frame_count = 0
            self._last_result = None  # Clear cached result
            
            started = time.perf_counter()
            try:
                # Check if we should skip this frame
                skip_every = self._config.capture.skip_frames
                
                if skip_every > 1:
                    frame_count += 1
                    if frame_count % skip_every != 1:
                        # Skip OCR, use last result
                        if self._last_result is not None:
                            result, cursor_pos = self._last_result
                            elapsed_ms = (time.perf_counter() - started) * 1000.0
                            payload = self._build_overlay_payload(
                                cursor_pos, 
                                result, 
                                elapsed_ms, 
                                None
                            )
                            self.overlay_show.emit(payload)
                            continue
                
                # Run OCR detection
                result, cursor_pos, debug_image = self._detect()
                self._last_result = (result, cursor_pos)  # Cache for skipping
                
                # Show debug overlay only once per activation
                if self._debug_overlay is not None and not self._debug_shown_this_activation:
                    self._debug_shown_this_activation = True
                    ocr_region_for_debug = (
                        self._ocr_region["left"], 
                        self._ocr_region["top"], 
                        self._ocr_region["width"], 
                        self._ocr_region["height"]
                    )
                    self._debug_overlay.show_debug(
                        debug_image, 
                        ocr_region_for_debug, 
                        cursor_pos
                    )
                
                # Apply stability check
                result = self._stabilize_result(result)
                
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                
                # Build and emit overlay payload
                payload = self._build_overlay_payload(
                    cursor_pos, 
                    result, 
                    elapsed_ms, 
                    debug_image
                )
                self.overlay_show.emit(payload)
                
            except Exception:
                LOGGER.exception("Detection loop error.")
                self.overlay_show.emit(
                    OverlayPayload(
                        cursor_pos=(0, 0),
                        title="Error",
                        body="Check logs and try again.",
                        confidence_text="Runtime error",
                        matched=False,
                        debug_image=None,
                        ocr_region=None,
                    )
                )
                time.sleep(0.20)
                continue

            # Maintain poll interval
            elapsed = time.perf_counter() - started
            sleep_for = poll_seconds - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
    
    def _detect(self) -> tuple[MatchResult, tuple[int, int], np.ndarray | None]:
        """
        Perform OCR detection on screen capture.
        
        Returns:
            Tuple of (MatchResult, cursor_pos, debug_image)
        """
        roi_bgr, cursor_pos, _region = self._capture.capture_around_cursor()
        
        debug_image = None
        # Draw debug info if debug mode enabled
        if self._config.debug and roi_bgr is not None and roi_bgr.size > 0:
            debug_image = roi_bgr.copy()
            
            x = self._ocr_region["left"]
            y = self._ocr_region["top"]
            w = self._ocr_region["width"]
            h = self._ocr_region["height"]
            
            # Draw OCR region rectangle
            if 0 <= x < roi_bgr.shape[1] and 0 <= y < roi_bgr.shape[0]:
                x2 = min(x + w, roi_bgr.shape[1])
                y2 = min(y + h, roi_bgr.shape[0])
                cv2.rectangle(debug_image, (x, y), (x2, y2), (0, 0, 255), 3)
                cv2.putText(
                    debug_image, "OCR", (x, y - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2
                )
            
            # Draw ROI size info
            cv2.putText(
                debug_image, 
                f"ROI: {roi_bgr.shape[1]}x{roi_bgr.shape[0]}", 
                (10, roi_bgr.shape[0] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1
            )
        
        # Run OCR detection
        item_name = self._ocr_detector.detect_from_image(roi_bgr, self._ocr_region)
        
        # Build result
        if item_name and item_name in self._items_by_name:
            item = self._items_by_name[item_name]
            return MatchResult(
                matched=True,
                confidence=1.0,
                threshold=0.5,
                item=item,
                best_item=item,
                message=item.info or f"Matched '{item.name}'",
            ), cursor_pos, debug_image
        
        return MatchResult(
            matched=False,
            confidence=0.0,
            threshold=0.5,
            item=None,
            best_item=None,
            message="No match found",
        ), cursor_pos, debug_image

    def _reset_temporal_state(self) -> None:
        """Reset stability tracking state."""
        self._last_item_name = None
        self._item_streak = 0

    def _stabilize_result(self, result: MatchResult) -> MatchResult:
        """
        Apply stability check to avoid flickering.
        
        Requires 2 consecutive detections of the same item.
        """
        if result.item is None:
            self._reset_temporal_state()
            return result

        current_name = result.item.name
        
        if current_name == self._last_item_name:
            self._item_streak += 1
        else:
            self._last_item_name = current_name
            self._item_streak = 1

        # Require 2 consecutive matches
        stable = self._item_streak >= 2

        if stable:
            return result

        return MatchResult(
            matched=False,
            confidence=result.confidence,
            threshold=result.threshold,
            item=result.item,
            best_item=result.best_item,
            message="Stabilizing...",
        )

    def _build_overlay_payload(
        self,
        cursor_pos: tuple[int, int],
        result: MatchResult,
        elapsed_ms: float,
        debug_image: np.ndarray | None = None,
    ) -> OverlayPayload:
        """
        Build overlay payload from detection result.
        
        Shows matched item info or detected text.
        """
        detected_text = self._ocr_detector.last_detected_text if self._ocr_detector else None
        
        if result.matched and result.item is not None:
            title = result.item.name
            body = result.message
            matched = True
        else:
            title = "No match"
            if detected_text:
                body = f"Detected: '{detected_text}'"
            else:
                body = "Move cursor over an item name in the game."
            matched = False

        # Show timing in debug mode
        confidence_text = f"{elapsed_ms:.1f} ms" if self._config.debug else ""

        # Include OCR region in debug mode
        ocr_region = None
        if self._config.debug:
            ocr_region = (
                self._ocr_region["left"], 
                self._ocr_region["top"], 
                self._ocr_region["width"], 
                self._ocr_region["height"]
            )
        
        return OverlayPayload(
            cursor_pos=cursor_pos,
            title=title,
            body=body,
            confidence_text=confidence_text,
            matched=matched,
            debug_image=debug_image,
            ocr_region=ocr_region,
        )
