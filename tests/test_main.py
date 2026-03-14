"""Tests for main.py configuration and CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.settings_manager import SettingsManager


def _build_config_with_defaults(args):
    """Helper to build config with default settings."""
    from main import parse_args, build_config
    
    settings = SettingsManager()
    return build_config(args, settings)


def test_default_config():
    """Test that default values are sensible."""
    from main import parse_args
    
    args = parse_args([])
    config = _build_config_with_defaults(args)
    
    assert config.debug is False
    assert config.capture.roi_width == 1200
    assert config.capture.roi_height == 800
    assert config.capture.poll_interval_ms == 75
    assert config.capture.skip_frames == 7
    assert config.ocr.region_x == 0
    assert config.ocr.region_y == 0
    assert config.ocr.region_width == 0
    assert config.ocr.region_height == 0


def test_debug_flag():
    """Test --debug flag."""
    from main import parse_args
    
    args = parse_args(['--debug'])
    config = _build_config_with_defaults(args)
    
    assert config.debug is True


def test_roi_width():
    """Test --roi-width flag."""
    from main import parse_args
    
    args = parse_args(['--roi-width', '400'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.roi_width == 400


def test_roi_width_minimum():
    """Test that roi-width has minimum value."""
    from main import parse_args
    
    args = parse_args(['--roi-width', '10'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.roi_width == 24  # minimum


def test_roi_height():
    """Test --roi-height flag."""
    from main import parse_args
    
    args = parse_args(['--roi-height', '300'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.roi_height == 300


def test_roi_height_minimum():
    """Test that roi-height has minimum value."""
    from main import parse_args
    
    args = parse_args(['--roi-height', '10'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.roi_height == 24  # minimum


def test_poll_interval():
    """Test --poll-ms flag."""
    from main import parse_args
    
    args = parse_args(['--poll-ms', '100'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.poll_interval_ms == 100


def test_poll_interval_minimum():
    """Test that poll-ms has minimum value."""
    from main import parse_args
    
    args = parse_args(['--poll-ms', '10'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.poll_interval_ms == 25  # minimum


def test_skip_frames():
    """Test --skip-frames flag."""
    from main import parse_args
    
    args = parse_args(['--skip-frames', '3'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.skip_frames == 3


def test_skip_frames_minimum():
    """Test that skip-frames has minimum value of 1."""
    from main import parse_args
    
    args = parse_args(['--skip-frames', '0'])
    config = _build_config_with_defaults(args)
    
    assert config.capture.skip_frames == 1  # minimum


def test_ocr_region_default():
    """Test default OCR region is full ROI."""
    from main import parse_args
    
    args = parse_args([])
    config = _build_config_with_defaults(args)
    
    assert config.ocr.region_x == 0
    assert config.ocr.region_y == 0
    assert config.ocr.region_width == 0
    assert config.ocr.region_height == 0


def test_ocr_region_custom():
    """Test custom OCR region."""
    from main import parse_args
    
    args = parse_args(['--ocr-region', '100,50,200,40'])
    config = _build_config_with_defaults(args)
    
    assert config.ocr.region_x == 100
    assert config.ocr.region_y == 50
    assert config.ocr.region_width == 200
    assert config.ocr.region_height == 40


def test_ocr_region_invalid():
    """Test that invalid OCR region falls back to default."""
    from main import parse_args
    
    args = parse_args(['--ocr-region', 'invalid'])
    config = _build_config_with_defaults(args)
    
    # Should fall back to default
    assert config.ocr.region_x == 0
    assert config.ocr.region_y == 0
    assert config.ocr.region_width == 0
    assert config.ocr.region_height == 0
