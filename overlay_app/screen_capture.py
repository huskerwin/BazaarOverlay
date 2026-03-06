from __future__ import annotations

import ctypes
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
    def __init__(self, roi_radius: int):
        self._roi_radius = max(24, roi_radius)
        self._mss = mss.mss()
        self._desktop = self._mss.monitors[0]

    def capture_around_cursor(self) -> tuple[np.ndarray, tuple[int, int], CaptureRegion]:
        cursor_x, cursor_y = win32api.GetCursorPos()

        left = max(self._desktop["left"], cursor_x - self._roi_radius)
        top = max(self._desktop["top"], cursor_y - self._roi_radius)

        right_limit = self._desktop["left"] + self._desktop["width"]
        bottom_limit = self._desktop["top"] + self._desktop["height"]

        right = min(right_limit, cursor_x + self._roi_radius)
        bottom = min(bottom_limit, cursor_y + self._roi_radius)

        region: CaptureRegion = {
            "left": int(left),
            "top": int(top),
            "width": max(2, int(right - left)),
            "height": max(2, int(bottom - top)),
        }

        frame = np.asarray(self._mss.grab(region), dtype=np.uint8)[:, :, :3]
        return frame, (cursor_x, cursor_y), region
