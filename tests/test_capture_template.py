from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import capture_template


def test_parse_args_defaults_to_hotkey_box(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["capture_template.py", "iron_sword"],
    )

    args = capture_template.parse_args()

    assert args.item_id == "iron_sword"
    assert args.mode == "hotkey-box"


def test_main_uses_hotkey_box_mode_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    frame = np.zeros((12, 10, 3), dtype=np.uint8)
    called = {"box": False}

    def fake_capture_by_hotkey_box() -> np.ndarray:
        called["box"] = True
        return frame

    def fake_imwrite(path: str, image: np.ndarray) -> bool:
        called["path"] = path
        called["shape"] = image.shape
        return True

    monkeypatch.setattr(capture_template, "enable_dpi_awareness", lambda: None)
    monkeypatch.setattr(capture_template, "capture_by_hotkey_box", fake_capture_by_hotkey_box)
    monkeypatch.setattr(capture_template.cv2, "imwrite", fake_imwrite)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_template.py",
            "iron_sword",
            "--output-dir",
            str(tmp_path),
            "--threshold",
            "0.82",
            "--name",
            "Iron Sword",
        ],
    )

    exit_code = capture_template.main()
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert called["box"] is True
    assert Path(called["path"]).name == "iron_sword.png"
    assert called["shape"] == frame.shape
    assert "Saved template:" in stdout
    assert '"id": "iron_sword"' in stdout


def test_main_cursor_mode_passes_size_and_countdown(monkeypatch, tmp_path: Path) -> None:
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    called: dict[str, int | tuple[int, int, int] | str] = {}

    def fake_capture_around_cursor(capture_size: int, countdown: int) -> np.ndarray:
        called["capture_size"] = capture_size
        called["countdown"] = countdown
        return frame

    def fake_imwrite(path: str, image: np.ndarray) -> bool:
        called["path"] = path
        called["shape"] = image.shape
        return True

    monkeypatch.setattr(capture_template, "enable_dpi_awareness", lambda: None)
    monkeypatch.setattr(capture_template, "capture_around_cursor", fake_capture_around_cursor)
    monkeypatch.setattr(capture_template.cv2, "imwrite", fake_imwrite)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_template.py",
            "gem",
            "--mode",
            "cursor",
            "--size",
            "64",
            "--countdown",
            "2",
            "--output-dir",
            str(tmp_path),
        ],
    )

    exit_code = capture_template.main()

    assert exit_code == 0
    assert called["capture_size"] == 64
    assert called["countdown"] == 2
    assert Path(str(called["path"])).name == "gem.png"
    assert called["shape"] == frame.shape


def test_main_returns_130_when_capture_is_canceled(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_capture_by_hotkey_box() -> np.ndarray:
        raise KeyboardInterrupt

    monkeypatch.setattr(capture_template, "enable_dpi_awareness", lambda: None)
    monkeypatch.setattr(capture_template, "capture_by_hotkey_box", fake_capture_by_hotkey_box)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "capture_template.py",
            "canceled_item",
            "--output-dir",
            str(tmp_path),
        ],
    )

    exit_code = capture_template.main()
    stdout = capsys.readouterr().out

    assert exit_code == 130
    assert "Capture canceled." in stdout
