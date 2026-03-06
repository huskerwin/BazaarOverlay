from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app import screen_capture


class _FakeMSSCapture:
    def __init__(self, desktop: dict[str, int]) -> None:
        self.monitors = [desktop]
        self.grab_calls: list[dict[str, int]] = []

    def grab(self, region: dict[str, int]) -> np.ndarray:
        self.grab_calls.append(region)
        return np.zeros((region["height"], region["width"], 4), dtype=np.uint8)


def test_screen_capture_uses_thread_local_sessions(monkeypatch) -> None:
    desktop = {"left": 0, "top": 0, "width": 300, "height": 200}
    captures: list[_FakeMSSCapture] = []

    def fake_mss() -> _FakeMSSCapture:
        capture = _FakeMSSCapture(desktop)
        captures.append(capture)
        return capture

    monkeypatch.setattr(screen_capture.mss, "mss", fake_mss)
    monkeypatch.setattr(screen_capture.win32api, "GetCursorPos", lambda: (100, 100))

    capture = screen_capture.ScreenCapture(roi_radius=24)

    frame_1, cursor_1, region_1 = capture.capture_around_cursor()
    frame_2, cursor_2, region_2 = capture.capture_around_cursor()

    assert len(captures) == 1
    assert len(captures[0].grab_calls) == 2
    assert frame_1.shape == (48, 48, 3)
    assert frame_2.shape == (48, 48, 3)
    assert cursor_1 == (100, 100)
    assert cursor_2 == (100, 100)
    assert region_1 == region_2

    out: queue.Queue[tuple[int, int, int]] = queue.Queue()

    def worker() -> None:
        frame, _cursor, _region = capture.capture_around_cursor()
        out.put(frame.shape)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert out.get_nowait() == (48, 48, 3)
    assert len(captures) == 2
    assert len(captures[1].grab_calls) == 1
