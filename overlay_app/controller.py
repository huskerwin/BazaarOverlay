from __future__ import annotations

import logging
import threading
import time

from PySide6.QtCore import QObject, Signal

from .config import AppConfig
from .hotkey_listener import HoldHotkeyListener
from .models import ItemDefinition, MatchResult, OverlayPayload
from .overlay_window import OverlayWindow
from .screen_capture import ScreenCapture
from .template_matcher import TemplateMatcher

LOGGER = logging.getLogger("overlay.controller")


class AppController(QObject):
    overlay_show = Signal(object)
    overlay_hide = Signal()

    def __init__(self, config: AppConfig, items: list[ItemDefinition], overlay: OverlayWindow):
        super().__init__()
        self._config = config

        self._overlay = overlay
        self._capture = ScreenCapture(config.capture.roi_radius)
        self._matcher = TemplateMatcher(items=items, config=config.matching)
        self._hotkey = HoldHotkeyListener(on_state_change=self._on_hotkey_state, trigger_key="e")

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
            self.overlay_hide.emit()

    def _worker_loop(self) -> None:
        poll_seconds = self._config.capture.poll_interval_ms / 1000.0

        while not self._shutdown_event.is_set():
            if not self._active_event.wait(timeout=0.10):
                continue

            started = time.perf_counter()
            try:
                roi_bgr, cursor_pos, _region = self._capture.capture_around_cursor()
                result = self._matcher.match(roi_bgr)
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                payload = self._build_overlay_payload(cursor_pos, result, elapsed_ms)
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
                    )
                )
                time.sleep(0.20)
                continue

            elapsed = time.perf_counter() - started
            sleep_for = poll_seconds - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _build_overlay_payload(
        self,
        cursor_pos: tuple[int, int],
        result: MatchResult,
        elapsed_ms: float,
    ) -> OverlayPayload:
        if result.matched and result.item is not None:
            title = result.item.name
            body = result.message
            matched = True
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
        )
