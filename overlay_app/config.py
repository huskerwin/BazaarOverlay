"""
Configuration dataclasses for Bazaar Overlay.

Defines capture, OCR, and overlay settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CaptureConfig:
    """Screen capture configuration."""
    roi_radius: int = 400  # Radius around cursor to capture
    poll_interval_ms: int = 75  # Detection loop interval


@dataclass(frozen=True)
class OcrConfig:
    """OCR detection configuration."""
    enabled: bool = True  # OCR is always enabled
    region_x: int = 500   # X offset from cursor (right positive)
    region_y: int = -50   # Y offset from cursor (down positive, negative = up)
    region_width: int = 200  # Width of OCR region
    region_height: int = 40   # Height of OCR region


@dataclass(frozen=True)
class OverlayConfig:
    """Overlay window configuration."""
    width: int = 336  # Overlay width in pixels
    min_height: int = 100  # Minimum overlay height
    x_offset: int = 20  # X offset from cursor
    y_offset: int = 24  # Y offset from cursor


@dataclass(frozen=True)
class AppConfig:
    """Main application configuration."""
    items_path: Path  # Path to items.json
    debug: bool = False  # Enable debug mode
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    ocr: OcrConfig = field(default_factory=OcrConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
