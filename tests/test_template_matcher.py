from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.config import MatchConfig
from overlay_app.models import ItemDefinition
from overlay_app.template_matcher import TemplateMatcher


def _write_template(path: Path, kind: str) -> np.ndarray:
    image = np.full((20, 20), 20, dtype=np.uint8)

    if kind == "circle":
        cv2.circle(image, (10, 10), 6, 220, -1)
    elif kind == "diamond":
        points = np.array([[10, 3], [17, 10], [10, 17], [3, 10]], dtype=np.int32)
        cv2.fillConvexPoly(image, points, 210)
    else:
        raise ValueError(f"Unsupported template kind: {kind}")

    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise RuntimeError(f"Failed to write template: {path}")
    return image


def _item(name: str, template_path: Path, threshold: float = 0.75) -> ItemDefinition:
    return ItemDefinition(
        item_id=name.lower(),
        name=name,
        template_paths=(template_path,),
        info=f"Info for {name}",
        threshold=threshold,
    )


def test_matcher_returns_best_match_for_exact_template(tmp_path: Path) -> None:
    coin_path = tmp_path / "coin.png"
    gem_path = tmp_path / "gem.png"
    coin_template = _write_template(coin_path, "circle")
    _write_template(gem_path, "diamond")

    matcher = TemplateMatcher(
        items=[_item("Coin", coin_path), _item("Gem", gem_path)],
        config=MatchConfig(global_threshold=0.70, scales=(1.0,)),
    )

    roi_gray = np.full((72, 72), 15, dtype=np.uint8)
    height, width = coin_template.shape
    roi_gray[24 : 24 + height, 26 : 26 + width] = coin_template
    roi_bgr = cv2.cvtColor(roi_gray, cv2.COLOR_GRAY2BGR)

    result = matcher.match(roi_bgr)

    assert result.matched is True
    assert result.item is not None
    assert result.item.name == "Coin"
    assert result.best_item is not None
    assert result.best_item.name == "Coin"
    assert result.confidence >= result.threshold


def test_matcher_returns_no_confident_match_for_unrelated_roi(tmp_path: Path) -> None:
    coin_path = tmp_path / "coin.png"
    gem_path = tmp_path / "gem.png"
    _write_template(coin_path, "circle")
    _write_template(gem_path, "diamond")

    matcher = TemplateMatcher(
        items=[_item("Coin", coin_path, threshold=0.90), _item("Gem", gem_path, threshold=0.90)],
        config=MatchConfig(global_threshold=0.90, scales=(1.0,)),
    )

    roi_bgr = np.zeros((72, 72, 3), dtype=np.uint8)
    result = matcher.match(roi_bgr)

    assert result.matched is False
    assert result.item is None
    assert result.best_item is not None
    assert result.message == "No confident match found."
    assert result.confidence < result.threshold


def test_matcher_reports_when_roi_is_too_small(tmp_path: Path) -> None:
    coin_path = tmp_path / "coin.png"
    _write_template(coin_path, "circle")

    matcher = TemplateMatcher(
        items=[_item("Coin", coin_path)],
        config=MatchConfig(global_threshold=0.80, scales=(1.0,)),
    )

    small_roi = np.zeros((8, 8, 3), dtype=np.uint8)
    result = matcher.match(small_roi)

    assert result.matched is False
    assert result.best_item is None
    assert result.message == "No template fits the current capture size."


def test_matcher_reports_empty_capture_region(tmp_path: Path) -> None:
    coin_path = tmp_path / "coin.png"
    _write_template(coin_path, "circle")

    matcher = TemplateMatcher(
        items=[_item("Coin", coin_path)],
        config=MatchConfig(global_threshold=0.80, scales=(1.0,)),
    )

    empty = np.array([], dtype=np.uint8)
    result = matcher.match(empty)

    assert result.matched is False
    assert result.best_item is None
    assert result.confidence == 0.0
    assert result.message == "Empty capture region."


def test_matcher_exposes_minimum_roi_radius_from_template_size(tmp_path: Path) -> None:
    template_path = tmp_path / "wide_template.png"
    wide_template = np.full((20, 40), 25, dtype=np.uint8)
    cv2.rectangle(wide_template, (6, 5), (33, 14), 210, -1)
    ok = cv2.imwrite(str(template_path), wide_template)
    assert ok is True

    matcher = TemplateMatcher(
        items=[_item("Wide", template_path)],
        config=MatchConfig(global_threshold=0.80, scales=(1.0,)),
    )

    assert matcher.minimum_roi_radius == 26


def test_matcher_orb_stage_can_promote_shortlisted_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    coin_path = tmp_path / "coin.png"
    gem_path = tmp_path / "gem.png"
    _write_template(coin_path, "circle")
    _write_template(gem_path, "diamond")

    matcher = TemplateMatcher(
        items=[_item("Coin", coin_path, threshold=0.30), _item("Gem", gem_path, threshold=0.30)],
        config=MatchConfig(global_threshold=0.30, scales=(1.0,), shortlist_size=2, orb_weight=0.50),
    )

    monkeypatch.setattr(
        matcher,
        "_score_variant_template",
        lambda _roi_gray, _roi_edges, variant: 0.95 if variant.item.name == "Coin" else 0.90,
    )
    monkeypatch.setattr(
        matcher,
        "_orb_score_for_variant",
        lambda variant, _roi_desc, _roi_kp: 0.10 if variant.item.name == "Coin" else 0.95,
    )

    roi_bgr = np.zeros((72, 72, 3), dtype=np.uint8)
    result = matcher.match(roi_bgr)

    assert result.matched is True
    assert result.best_item is not None
    assert result.best_item.name == "Gem"
