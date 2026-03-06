from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app import controller as controller_module
from overlay_app.config import AppConfig, CaptureConfig, MatchConfig
from overlay_app.models import ItemDefinition, MatchResult


class _DummyOverlay:
    def show_payload(self, _payload) -> None:
        return

    def hide_overlay(self) -> None:
        return


class _DummyScreenCapture:
    def __init__(self, roi_radius: int):
        self.roi_radius = roi_radius


class _DummyMatcher:
    def __init__(self, items, config):
        self.minimum_roi_radius = 24


class _DummyHotkey:
    def __init__(self, on_state_change, trigger_key):
        self._on_state_change = on_state_change
        self._trigger_key = trigger_key

    def start(self) -> None:
        return

    def stop(self) -> None:
        return


def _item(item_id: str, name: str) -> ItemDefinition:
    return ItemDefinition(
        item_id=item_id,
        name=name,
        template_paths=(Path(f"{item_id}.png"),),
        info=f"Info for {name}",
        threshold=0.80,
    )


def _result(item: ItemDefinition, confidence: float) -> MatchResult:
    return MatchResult(
        matched=confidence >= 0.80,
        confidence=confidence,
        threshold=0.80,
        item=item if confidence >= 0.80 else None,
        best_item=item,
        message=item.info,
    )


def test_controller_temporal_smoothing_requires_stable_frames(monkeypatch) -> None:
    monkeypatch.setattr(controller_module, "ScreenCapture", _DummyScreenCapture)
    monkeypatch.setattr(controller_module, "TemplateMatcher", _DummyMatcher)
    monkeypatch.setattr(controller_module, "HoldHotkeyListener", _DummyHotkey)

    config = AppConfig(
        items_path=Path("data/items.json"),
        capture=CaptureConfig(roi_radius=72, poll_interval_ms=75),
        matching=MatchConfig(stable_frames_required=2, temporal_smoothing_alpha=0.60),
    )

    chest = _item("chest", "Chest")
    rank = _item("rank", "Rank")

    controller = controller_module.AppController(config=config, items=[chest], overlay=_DummyOverlay())

    first = controller._stabilize_result(_result(chest, 0.92))
    second = controller._stabilize_result(_result(chest, 0.91))
    switched = controller._stabilize_result(_result(rank, 0.93))

    assert first.matched is False
    assert first.message == "Stabilizing match..."
    assert second.matched is True
    assert second.item is not None
    assert second.item.item_id == "chest"
    assert switched.matched is False
    assert switched.best_item is not None
    assert switched.best_item.item_id == "rank"
