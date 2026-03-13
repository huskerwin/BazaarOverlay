"""Tests for overlay_app models."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.models import ItemDefinition, MatchResult, OverlayPayload, OcrRegion


class TestItemDefinition:
    def test_item_definition_basic(self):
        item = ItemDefinition(item_id="sword", name="Sword")
        assert item.item_id == "sword"
        assert item.name == "Sword"
        assert item.info == ""
        assert item.enchantments is None

    def test_item_definition_with_info(self):
        item = ItemDefinition(item_id="sword", name="Sword", info="A sharp blade")
        assert item.info == "A sharp blade"

    def test_item_definition_with_enchantments(self):
        enchantments = {"golden": "Double value", "heavy": "Slows twice"}
        item = ItemDefinition(
            item_id="sword",
            name="Sword",
            info="A sharp blade",
            enchantments=enchantments,
        )
        assert item.enchantments == enchantments
        assert item.enchantments["golden"] == "Double value"

    def test_item_definition_immutable(self):
        item = ItemDefinition(item_id="sword", name="Sword")
        with pytest.raises(AttributeError):
            item.name = "New Name"


class TestOverlayPayload:
    def test_overlay_payload_basic(self):
        payload = OverlayPayload(
            cursor_pos=(100, 200),
            title="Test Title",
            body="Test body",
            confidence_text="95%",
            matched=True,
        )
        assert payload.cursor_pos == (100, 200)
        assert payload.title == "Test Title"
        assert payload.body == "Test body"
        assert payload.confidence_text == "95%"
        assert payload.matched is True
        assert payload.debug_image is None
        assert payload.ocr_region is None
        assert payload.enchantments is None

    def test_overlay_payload_with_optional_fields(self):
        import numpy as np

        debug_img = np.zeros((10, 10, 3), dtype=np.uint8)
        enchantments = {"golden": "Double value"}
        payload = OverlayPayload(
            cursor_pos=(100, 200),
            title="Test Title",
            body="Test body",
            confidence_text="95%",
            matched=True,
            debug_image=debug_img,
            ocr_region=(10, 20, 100, 50),
            enchantments=enchantments,
        )
        assert payload.debug_image is debug_img
        assert payload.ocr_region == (10, 20, 100, 50)
        assert payload.enchantments == enchantments

    def test_overlay_payload_with_enchantments_only(self):
        enchantments = {"golden": "Double value", "heavy": "Slows"}
        payload = OverlayPayload(
            cursor_pos=(0, 0),
            title="Item",
            body="Info",
            confidence_text="",
            matched=True,
            enchantments=enchantments,
        )
        assert payload.enchantments == enchantments
        assert len(payload.enchantments) == 2


class TestMatchResult:
    def test_match_result_matched(self):
        item = ItemDefinition(item_id="sword", name="Sword")
        result = MatchResult(
            matched=True,
            confidence=0.95,
            threshold=0.8,
            item=item,
            best_item=item,
            message="Matched Sword",
        )
        assert result.matched is True
        assert result.confidence == 0.95
        assert result.item == item

    def test_match_result_not_matched(self):
        result = MatchResult(
            matched=False,
            confidence=0.3,
            threshold=0.8,
            item=None,
            best_item=None,
            message="No match",
        )
        assert result.matched is False
        assert result.item is None


class TestOcrRegion:
    def test_ocr_region_creation(self):
        region: OcrRegion = {"left": 10, "top": 20, "width": 100, "height": 50}
        assert region["left"] == 10
        assert region["top"] == 20
        assert region["width"] == 100
        assert region["height"] == 50
