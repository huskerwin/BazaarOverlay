from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import cv2
import mss
import numpy as np
import win32api
from pynput import keyboard

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.screen_capture import enable_dpi_awareness

SHIFT_KEYS = (
    keyboard.Key.shift,
    keyboard.Key.shift_l,
    keyboard.Key.shift_r,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a template image by pressing Shift+C and drawing a box, "
            "or by using cursor mode."
        )
    )
    parser.add_argument("item_id", help="Template filename stem, for example iron_sword")
    parser.add_argument(
        "--mode",
        choices=("hotkey-box", "cursor"),
        default="hotkey-box",
        help="Capture mode. 'hotkey-box' waits for Shift+C and lets you draw a box.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets/templates"),
        help="Directory where template image will be saved.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=56,
        help="Square capture size in pixels.",
    )
    parser.add_argument(
        "--countdown",
        type=int,
        default=3,
        help="Seconds to wait before capture.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.82,
        help="Suggested threshold to print in JSON snippet.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="",
        help="Display name for the printed JSON snippet.",
    )
    return parser.parse_args()


def capture_around_cursor(capture_size: int, countdown: int) -> np.ndarray:
    half = capture_size // 2

    if countdown > 0:
        for remaining in range(countdown, 0, -1):
            print(f"Capturing in {remaining}...")
            time.sleep(1)

    cursor_x, cursor_y = win32api.GetCursorPos()

    with mss.mss() as sct:
        desktop = sct.monitors[0]
        left = max(desktop["left"], cursor_x - half)
        top = max(desktop["top"], cursor_y - half)
        right = min(desktop["left"] + desktop["width"], left + capture_size)
        bottom = min(desktop["top"] + desktop["height"], top + capture_size)

        region = {
            "left": int(left),
            "top": int(top),
            "width": max(2, int(right - left)),
            "height": max(2, int(bottom - top)),
        }
        return np.asarray(sct.grab(region), dtype=np.uint8)[:, :, :3]


def wait_for_shift_c() -> None:
    print("Focus the game, then press Shift+C to start box selection.")
    print("Press Esc to cancel.")

    ready = threading.Event()
    canceled = threading.Event()
    state = {"shift_down": False}

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return

        if key in SHIFT_KEYS:
            state["shift_down"] = True
            return

        if key == keyboard.Key.esc:
            canceled.set()
            ready.set()
            return

        if isinstance(key, keyboard.KeyCode) and key.char is not None:
            if key.char.lower() == "c" and state["shift_down"]:
                ready.set()
                return

        return

    def on_release(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return
        if key in SHIFT_KEYS:
            state["shift_down"] = False

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        ready.wait()
        listener.stop()

    if canceled.is_set():
        raise KeyboardInterrupt


def capture_by_hotkey_box() -> np.ndarray:
    wait_for_shift_c()

    with mss.mss() as sct:
        desktop = sct.monitors[0]
        screenshot = np.asarray(sct.grab(desktop), dtype=np.uint8)[:, :, :3]

    window_name = "Template Selector"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    except cv2.error:
        pass

    print("Drag a box, then press Enter/Space to confirm or C to cancel.")
    x, y, width, height = cv2.selectROI(
        window_name,
        screenshot,
        showCrosshair=True,
        fromCenter=False,
    )
    cv2.destroyWindow(window_name)

    x = int(x)
    y = int(y)
    width = int(width)
    height = int(height)
    if width < 2 or height < 2:
        raise ValueError("Selection canceled or too small.")

    return screenshot[y : y + height, x : x + width]


def main() -> int:
    args = parse_args()
    enable_dpi_awareness()

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    item_id = args.item_id.strip().lower().replace(" ", "_")
    if not item_id:
        raise ValueError("item_id cannot be empty")

    try:
        if args.mode == "cursor":
            capture_size = max(16, int(args.size))
            frame = capture_around_cursor(capture_size=capture_size, countdown=max(0, int(args.countdown)))
        else:
            frame = capture_by_hotkey_box()
    except KeyboardInterrupt:
        print("Capture canceled.")
        return 130
    except ValueError as exc:
        print(f"Capture canceled: {exc}")
        return 1

    output_path = output_dir / f"{item_id}.png"
    if not cv2.imwrite(str(output_path), frame):
        raise RuntimeError(f"Failed to write template: {output_path}")

    display_name = args.name.strip() or item_id.replace("_", " ").title()

    print(f"Saved template: {output_path.as_posix()}")
    print("Add this to data/items.json:")
    print("{")
    print(f'  "id": "{item_id}",')
    print(f'  "name": "{display_name}",')
    print(f'  "template": "{output_path.as_posix()}",')
    print(f'  "threshold": {max(0.05, min(0.99, float(args.threshold))):.2f},')
    print('  "info": "Describe this item here."')
    print("}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
