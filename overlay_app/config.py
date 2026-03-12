from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CaptureConfig:
    roi_radius: int = 150
    poll_interval_ms: int = 75


@dataclass(frozen=True)
class OcrConfig:
    enabled: bool = True
    region_x: int = 50
    region_y: int = 0
    region_width: int = 200
    region_height: int = 40


@dataclass(frozen=True)
class MatchConfig:
    global_threshold: float = 0.80
    scales: tuple[float, ...] = (0.90, 1.00, 1.10)
    gray_weight: float = 0.75
    edge_weight: float = 0.25
    center_bias_weight: float = 0.25
    shortlist_size: int = 3
    orb_weight: float = 0.15
    orb_ratio_test: float = 0.75
    orb_min_good_matches: int = 8
    temporal_smoothing_alpha: float = 0.60
    stable_frames_required: int = 2


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
    matching: MatchConfig = field(default_factory=MatchConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
