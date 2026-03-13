from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CaptureConfig:
    roi_radius: int = 400
    poll_interval_ms: int = 75


@dataclass(frozen=True)
class OcrConfig:
    enabled: bool = True
    region_x: int = 500
    region_y: int = -50
    region_width: int = 200
    region_height: int = 40


@dataclass(frozen=True)
class OverlayConfig:
    width: int = 336
    min_height: int = 100
    x_offset: int = 20
    y_offset: int = 24


@dataclass(frozen=True)
class AppConfig:
    items_path: Path
    debug: bool = False
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    ocr: OcrConfig = field(default_factory=OcrConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
