"""Tests for overlay_app config."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.config import AppConfig, CaptureConfig, OcrConfig, OverlayConfig


class TestCaptureConfig:
    """Test CaptureConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = CaptureConfig()
        
        assert config.roi_width == 800
        assert config.roi_height == 600
        assert config.poll_interval_ms == 75
        assert config.skip_frames == 1

    def test_custom_values(self):
        """Test custom values."""
        config = CaptureConfig(
            roi_width=1200,
            roi_height=800,
            poll_interval_ms=50,
            skip_frames=3,
        )
        
        assert config.roi_width == 1200
        assert config.roi_height == 800
        assert config.poll_interval_ms == 50
        assert config.skip_frames == 3

    def test_immutable(self):
        """Test that config is immutable (frozen dataclass)."""
        config = CaptureConfig()
        
        with pytest.raises(AttributeError):
            config.roi_width = 1000


class TestOcrConfig:
    """Test OcrConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = OcrConfig()
        
        assert config.enabled is True
        assert config.region_x == 0
        assert config.region_y == 0
        assert config.region_width == 0
        assert config.region_height == 0

    def test_custom_values(self):
        """Test custom values."""
        config = OcrConfig(
            region_x=100,
            region_y=50,
            region_width=200,
            region_height=100,
        )
        
        assert config.region_x == 100
        assert config.region_y == 50
        assert config.region_width == 200
        assert config.region_height == 100

    def test_immutable(self):
        """Test that config is immutable (frozen dataclass)."""
        config = OcrConfig()
        
        with pytest.raises(AttributeError):
            config.region_x = 100


class TestOverlayConfig:
    """Test OverlayConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = OverlayConfig()
        
        assert config.width == 450
        assert config.min_height == 100
        assert config.x_offset == 20
        assert config.y_offset == 24

    def test_custom_values(self):
        """Test custom values."""
        config = OverlayConfig(
            width=500,
            min_height=150,
            x_offset=30,
            y_offset=50,
        )
        
        assert config.width == 500
        assert config.min_height == 150
        assert config.x_offset == 30
        assert config.y_offset == 50

    def test_immutable(self):
        """Test that config is immutable (frozen dataclass)."""
        config = OverlayConfig()
        
        with pytest.raises(AttributeError):
            config.width = 600


class TestAppConfig:
    """Test AppConfig dataclass."""

    def test_requires_items_path(self):
        """Test that items_path is required."""
        config = AppConfig(items_path=Path("data/items.json"))
        
        assert config.items_path == Path("data/items.json")

    def test_defaults(self):
        """Test default values."""
        config = AppConfig(items_path=Path("data/items.json"))
        
        assert config.debug is False
        assert isinstance(config.capture, CaptureConfig)
        assert isinstance(config.ocr, OcrConfig)
        assert isinstance(config.overlay, OverlayConfig)

    def test_custom_nested_config(self):
        """Test custom nested configurations."""
        config = AppConfig(
            items_path=Path("custom/items.json"),
            debug=True,
            capture=CaptureConfig(roi_width=400, skip_frames=5),
            ocr=OcrConfig(region_x=10, region_y=20),
            overlay=OverlayConfig(width=600),
        )
        
        assert config.items_path == Path("custom/items.json")
        assert config.debug is True
        assert config.capture.roi_width == 400
        assert config.capture.skip_frames == 5
        assert config.ocr.region_x == 10
        assert config.ocr.region_y == 20
        assert config.overlay.width == 600

    def test_immutable(self):
        """Test that config is immutable (frozen dataclass)."""
        config = AppConfig(items_path=Path("data/items.json"))
        
        with pytest.raises(AttributeError):
            config.debug = True
