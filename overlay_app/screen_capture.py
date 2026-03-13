from __future__ import annotations

import ctypes
import threading
from typing import TypedDict

import mss
import numpy as np
import win32api


class CaptureRegion(TypedDict):
    left: int
    top: int
    width: int
    height: int


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ScreenCapture:
    def __init__(self, roi_width: int, roi_height: int):
        self._roi_width = max(24, roi_width)
        self._roi_height = max(24, roi_height)
        self._local = threading.local()

    def _session(self) -> tuple[mss.mss, dict[str, int]]:
        capture = getattr(self._local, "capture", None)
        if capture is None:
            capture = mss.mss()
            self._local.capture = capture
            self._local.desktop = capture.monitors[0]
        return capture, self._local.desktop

    def capture_around_cursor(self) -> tuple[np.ndarray, tuple[int, int], CaptureRegion]:
        capture, desktop = self._session()
        cursor_x, cursor_y = win32api.GetCursorPos()

        left = max(desktop["left"], cursor_x - self._roi_width // 2)
        top = max(desktop["top"], cursor_y - self._roi_height // 2)

        right_limit = desktop["left"] + desktop["width"]
        bottom_limit = desktop["top"] + desktop["height"]

        right = min(right_limit, cursor_x + (self._roi_width + 1) // 2)
        bottom = min(bottom_limit, cursor_y + (self._roi_height + 1) // 2)

        region: CaptureRegion = {
            "left": int(left),
            "top": int(top),
            "width": max(2, int(right - left)),
            "height": max(2, int(bottom - top)),
        }

        frame = np.asarray(capture.grab(region), dtype=np.uint8)[:, :, :3]
        return frame, (cursor_x, cursor_y), region
