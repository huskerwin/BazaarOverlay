from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import mss
import numpy as np
import win32api

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.screen_capture import enable_dpi_awareness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a template image around the current cursor position."
    )
    parser.add_argument("item_id", help="Template filename stem, for example iron_sword")
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


def main() -> int:
    args = parse_args()
    enable_dpi_awareness()

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    item_id = args.item_id.strip().lower().replace(" ", "_")
    if not item_id:
        raise ValueError("item_id cannot be empty")

    capture_size = max(16, int(args.size))
    half = capture_size // 2

    if args.countdown > 0:
        for remaining in range(args.countdown, 0, -1):
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
        frame = np.asarray(sct.grab(region), dtype=np.uint8)[:, :, :3]

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
