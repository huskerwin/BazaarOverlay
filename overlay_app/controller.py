from __future__ import annotations

import logging
import threading
import time
from typing import TypedDict

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

from .config import AppConfig
from .hotkey_listener import HoldHotkeyListener
from .models import ItemDefinition, MatchResult, OverlayPayload
from .ocr_detector import OcrItemDetector
from .overlay_window import OverlayWindow
from .screen_capture import ScreenCapture
from .template_matcher import TemplateMatcher

LOGGER = logging.getLogger("overlay.controller")


class OcrRegion(TypedDict):
    left: int
    top: int
    width: int
    height: int


class AppController(QObject):
    overlay_show = Signal(object)
    overlay_hide = Signal()

    def __init__(self, config: AppConfig, items: list[ItemDefinition], overlay: OverlayWindow):
        super().__init__()
        self._config = config

        self._stable_frames_required = max(1, int(config.matching.stable_frames_required))
        self._temporal_alpha = float(max(0.05, min(0.95, config.matching.temporal_smoothing_alpha)))
        self._last_candidate_id: str | None = None
        self._last_candidate_name: str | None = None
        self._candidate_streak = 0
        self._smoothed_confidence = 0.0

        self._overlay = overlay
        self._matcher = TemplateMatcher(items=items, config=config.matching)
        
        self._use_ocr = config.ocr.enabled
        self._show_ocr_region = config.debug and config.ocr.enabled
        if self._use_ocr:
            item_names = {item.name for item in items}
            self._ocr_detector = OcrItemDetector(item_names)
            self._ocr_region: OcrRegion = {
                "left": config.ocr.region_x,
                "top": config.ocr.region_y,
                "width": config.ocr.region_width,
                "height": config.ocr.region_height,
            }
            LOGGER.info("OCR detection enabled with region: %s", self._ocr_region)

        requested_radius = config.capture.roi_radius
        required_radius = self._matcher.minimum_roi_radius
        effective_radius = max(requested_radius, required_radius)
        if effective_radius != requested_radius:
            LOGGER.warning(
                "ROI radius %d is too small for current templates; using %d.",
                requested_radius,
                effective_radius,
            )

        self._capture = ScreenCapture(effective_radius)
        self._hotkey = HoldHotkeyListener(on_state_change=self._on_hotkey_state, trigger_key="e")
        
        self._items_by_name: dict[str, ItemDefinition] = {item.name: item for item in items}

        self._state_lock = threading.Lock()
        self._active = False

        self._active_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="item-detection-loop",
            daemon=True,
        )

        self.overlay_show.connect(self._overlay.show_payload)
        self.overlay_hide.connect(self._overlay.hide_overlay)

    def start(self) -> None:
        self._worker_thread.start()
        self._hotkey.start()

    def shutdown(self) -> None:
        self._hotkey.stop()
        self._active_event.clear()
        self._reset_temporal_state()
        self._shutdown_event.set()
        self.overlay_hide.emit()

        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

    def _on_hotkey_state(self, active: bool) -> None:
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

    def _worker_loop(self) -> None:
        poll_seconds = self._config.capture.poll_interval_ms / 1000.0

        while not self._shutdown_event.is_set():
            if not self._active_event.wait(timeout=0.10):
                continue

            started = time.perf_counter()
            try:
                debug_image = None
                if self._use_ocr:
                    result, cursor_pos, debug_image = self._ocr_detect()
                else:
                    roi_bgr, cursor_pos, _region = self._capture.capture_around_cursor()
                    result = self._matcher.match(roi_bgr)
                result = self._stabilize_result(result)
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                payload = self._build_overlay_payload(cursor_pos, result, elapsed_ms, debug_image)
                self.overlay_show.emit(payload)
            except Exception:
                LOGGER.exception("Detection loop error.")
                self.overlay_show.emit(
                    OverlayPayload(
                        cursor_pos=(0, 0),
                        title="Capture/Match Error",
                        body="Check logs and template files, then retry.",
                        confidence_text="Runtime error",
                        matched=False,
                        debug_image=None,
                    )
                )
                time.sleep(0.20)
                continue

            elapsed = time.perf_counter() - started
            sleep_for = poll_seconds - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
    
    def _ocr_detect(self) -> tuple[MatchResult, tuple[int, int]]:
        roi_bgr, cursor_pos, _region = self._capture.capture_around_cursor()
        
        debug_image = None
        if self._show_ocr_region and roi_bgr is not None and roi_bgr.size > 0:
            debug_image = roi_bgr.copy()
            
            x = self._ocr_region["left"]
            y = self._ocr_region["top"]
            w = self._ocr_region["width"]
            h = self._ocr_region["height"]
            
            if 0 <= x < roi_bgr.shape[1] and 0 <= y < roi_bgr.shape[0]:
                x2 = min(x + w, roi_bgr.shape[1])
                y2 = min(y + h, roi_bgr.shape[0])
                cv2.rectangle(debug_image, (x, y), (x2, y2), (0, 255, 0), 2)
        
        item_name = self._ocr_detector.detect_from_image(roi_bgr, self._ocr_region)
        
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
        self._last_candidate_id = None
        self._last_candidate_name = None
        self._candidate_streak = 0
        self._smoothed_confidence = 0.0

    def _stabilize_result(self, result: MatchResult) -> MatchResult:
        if result.best_item is None:
            self._reset_temporal_state()
            return result

        candidate_id = result.best_item.item_id
        if candidate_id == self._last_candidate_id:
            self._candidate_streak += 1
            self._smoothed_confidence = (
                (self._temporal_alpha * result.confidence)
                + ((1.0 - self._temporal_alpha) * self._smoothed_confidence)
            )
        else:
            self._last_candidate_id = candidate_id
            self._candidate_streak = 1
            self._smoothed_confidence = result.confidence

        stable = self._candidate_streak >= self._stable_frames_required
        smoothed_confidence = self._smoothed_confidence
        matched = stable and (smoothed_confidence >= result.threshold)

        if matched:
            item = result.best_item
            message = item.info or f"Matched '{item.name}'."
            return MatchResult(
                matched=True,
                confidence=smoothed_confidence,
                threshold=result.threshold,
                item=item,
                best_item=item,
                message=message,
            )

        message = result.message
        if not stable:
            message = "Stabilizing match..."

        return MatchResult(
            matched=False,
            confidence=smoothed_confidence,
            threshold=result.threshold,
            item=None,
            best_item=result.best_item,
            message=message,
        )

    def _build_overlay_payload(
        self,
        cursor_pos: tuple[int, int],
        result: MatchResult,
        elapsed_ms: float,
        debug_image: np.ndarray | None = None,
    ) -> OverlayPayload:
        if result.matched and result.item is not None:
            title = result.item.name
            body = result.message
            matched = True
        else:
            if result.message == "Stabilizing match...":
                title = "Stabilizing match..."
            else:
                title = "No confident match found."
            if result.best_item is None:
                body = "Move the cursor directly over an item icon and hold Shift+E."
            else:
                body = f"Best candidate: {result.best_item.name}"
            matched = False

        confidence_text = f"Score {result.confidence:.2f} | Threshold {result.threshold:.2f}"
        if self._config.debug:
            confidence_text = f"{confidence_text} | {elapsed_ms:.1f} ms"

        return OverlayPayload(
            cursor_pos=cursor_pos,
            title=title,
            body=body,
            confidence_text=confidence_text,
            matched=matched,
            debug_image=debug_image,
        )
