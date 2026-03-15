"""Tests for overlay_app controller."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.config import AppConfig, CaptureConfig, OcrConfig, OverlayConfig
from overlay_app.controller import AppController
from overlay_app.models import ItemDefinition


class TestAppControllerInit:
    """Test AppController initialization."""

    @patch('overlay_app.controller.HoldHotkeyListener')
    @patch('overlay_app.controller.ScreenCapture')
    @patch('overlay_app.controller.OcrItemDetector')
    def test_init_creates_components(self, mock_ocr, mock_capture, mock_hotkey):
        """Test that initialization creates necessary components."""
        mock_capture.return_value = MagicMock()
        mock_ocr.return_value = MagicMock()
        mock_hotkey.return_value = MagicMock()
        
        items = [ItemDefinition(item_id="sword", name="Sword")]
        config = AppConfig(
            items_path=Path("data/items.json"),
            capture=CaptureConfig(),
            ocr=OcrConfig(),
            overlay=OverlayConfig(),
        )
        
        mock_overlay = MagicMock()
        controller = AppController(
            config=config,
            items=items,
            overlay=mock_overlay,
        )
        
        assert controller._items_by_name is not None
        mock_capture.assert_called_once()
        mock_ocr.assert_called_once()

    @patch('overlay_app.controller.HoldHotkeyListener')
    @patch('overlay_app.controller.ScreenCapture')
    @patch('overlay_app.controller.OcrItemDetector')
    def test_init_creates_item_lookup(self, mock_ocr, mock_capture, mock_hotkey):
        """Test that initialization creates item lookup dictionary."""
        mock_capture.return_value = MagicMock()
        mock_ocr.return_value = MagicMock()
        mock_hotkey.return_value = MagicMock()
        
        items = [
            ItemDefinition(item_id="sword", name="Sword"),
            ItemDefinition(item_id="shield", name="Shield"),
            ItemDefinition(item_id="potion", name="Potion"),
        ]
        config = AppConfig(items_path=Path("data/items.json"))
        
        mock_overlay = MagicMock()
        controller = AppController(
            config=config,
            items=items,
            overlay=mock_overlay,
        )
        
        assert "Sword" in controller._items_by_name
        assert "Shield" in controller._items_by_name
        assert "Potion" in controller._items_by_name
        assert controller._items_by_name["Sword"].item_id == "sword"


class TestAppControllerSignals:
    """Test controller Qt signals."""

    @patch('overlay_app.controller.HoldHotkeyListener')
    @patch('overlay_app.controller.ScreenCapture')
    @patch('overlay_app.controller.OcrItemDetector')
    def test_has_overlay_show_signal(self, mock_ocr, mock_capture, mock_hotkey):
        """Test that controller has overlay_show signal."""
        mock_capture.return_value = MagicMock()
        mock_ocr.return_value = MagicMock()
        mock_hotkey.return_value = MagicMock()
        
        items = [ItemDefinition(item_id="sword", name="Sword")]
        config = AppConfig(items_path=Path("data/items.json"))
        
        mock_overlay = MagicMock()
        controller = AppController(
            config=config,
            items=items,
            overlay=mock_overlay,
        )
        
        assert hasattr(controller, 'overlay_show')
        assert hasattr(controller, 'overlay_hide')


class TestAppControllerTemporalState:
    """Test temporal state management."""

    @patch('overlay_app.controller.HoldHotkeyListener')
    @patch('overlay_app.controller.ScreenCapture')
    @patch('overlay_app.controller.OcrItemDetector')
    def test_reset_temporal_state(self, mock_ocr, mock_capture, mock_hotkey):
        """Test that reset_temporal_state clears all temporal data."""
        mock_capture.return_value = MagicMock()
        mock_ocr.return_value = MagicMock()
        mock_hotkey.return_value = MagicMock()
        
        items = [ItemDefinition(item_id="sword", name="Sword")]
        config = AppConfig(items_path=Path("data/items.json"))
        
        mock_overlay = MagicMock()
        controller = AppController(
            config=config,
            items=items,
            overlay=mock_overlay,
        )
        
        controller._last_item_name = "Sword"
        controller._item_streak = 5
        
        controller._reset_temporal_state()
        
        assert controller._last_item_name is None
        assert controller._item_streak == 0
