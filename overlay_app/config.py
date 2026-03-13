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
    skip_frames: int = 1  # Skip OCR every N frames (1 = no skip)


@dataclass(frozen=True)
class OcrConfig:
    """OCR detection configuration."""
    enabled: bool = True  # OCR is always enabled
    region_x: int = 0    # X offset from ROI (0 = use full width)
    region_y: int = 0     # Y offset from ROI (0 = use full height)
    region_width: int = 0  # 0 = full ROI width
    region_height: int = 0  # 0 = full ROI height


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
