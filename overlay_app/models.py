from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ItemDefinition:
    item_id: str
    name: str
    template_paths: tuple[Path, ...]
    info: str = ""
    threshold: float | None = None


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    confidence: float
    threshold: float
    item: ItemDefinition | None
    best_item: ItemDefinition | None
    message: str


@dataclass(frozen=True)
class OverlayPayload:
    cursor_pos: tuple[int, int]
    title: str
    body: str
    confidence_text: str
    matched: bool
    debug_image: np.ndarray | None = None
    ocr_region: tuple[int, int, int, int] | None = None
