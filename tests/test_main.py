"""Tests for main.py configuration and CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_default_config():
    """Test that default values are sensible."""
    from main import parse_args, build_config
    
    args = parse_args([])
    config = build_config(args)
    
    assert config.debug is False
    assert config.capture.roi_radius == 400
    assert config.capture.poll_interval_ms == 75
    assert config.capture.skip_frames == 1
    assert config.ocr.region_x == 0
    assert config.ocr.region_y == 0
    assert config.ocr.region_width == 0
    assert config.ocr.region_height == 0


def test_debug_flag():
    """Test --debug flag."""
    from main import parse_args, build_config
    
    args = parse_args(['--debug'])
    config = build_config(args)
    
    assert config.debug is True


def test_roi_radius():
    """Test --roi-radius flag."""
    from main import parse_args, build_config
    
    args = parse_args(['--roi-radius', '200'])
    config = build_config(args)
    
    assert config.capture.roi_radius == 200


def test_roi_radius_minimum():
    """Test that roi-radius has minimum value."""
    from main import parse_args, build_config
    
    args = parse_args(['--roi-radius', '10'])
    config = build_config(args)
    
    assert config.capture.roi_radius == 24  # minimum


def test_poll_interval():
    """Test --poll-ms flag."""
    from main import parse_args, build_config
    
    args = parse_args(['--poll-ms', '100'])
    config = build_config(args)
    
    assert config.capture.poll_interval_ms == 100


def test_poll_interval_minimum():
    """Test that poll-ms has minimum value."""
    from main import parse_args, build_config
    
    args = parse_args(['--poll-ms', '10'])
    config = build_config(args)
    
    assert config.capture.poll_interval_ms == 25  # minimum


def test_skip_frames():
    """Test --skip-frames flag."""
    from main import parse_args, build_config
    
    args = parse_args(['--skip-frames', '3'])
    config = build_config(args)
    
    assert config.capture.skip_frames == 3


def test_skip_frames_minimum():
    """Test that skip-frames has minimum value of 1."""
    from main import parse_args, build_config
    
    args = parse_args(['--skip-frames', '0'])
    config = build_config(args)
    
    assert config.capture.skip_frames == 1  # minimum


def test_ocr_region_default():
    """Test default OCR region is full ROI."""
    from main import parse_args, build_config
    
    args = parse_args([])
    config = build_config(args)
    
    assert config.ocr.region_x == 0
    assert config.ocr.region_y == 0
    assert config.ocr.region_width == 0
    assert config.ocr.region_height == 0


def test_ocr_region_custom():
    """Test custom OCR region."""
    from main import parse_args, build_config
    
    args = parse_args(['--ocr-region', '100,50,200,40'])
    config = build_config(args)
    
    assert config.ocr.region_x == 100
    assert config.ocr.region_y == 50
    assert config.ocr.region_width == 200
    assert config.ocr.region_height == 40


def test_ocr_region_invalid():
    """Test that invalid OCR region falls back to default."""
    from main import parse_args, build_config
    
    args = parse_args(['--ocr-region', 'invalid'])
    config = build_config(args)
    
    # Should fall back to default
    assert config.ocr.region_x == 0
    assert config.ocr.region_y == 0
    assert config.ocr.region_width == 0
    assert config.ocr.region_height == 0
