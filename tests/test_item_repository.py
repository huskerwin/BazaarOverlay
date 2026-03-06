from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.item_repository import ItemRepository


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_items_generates_id_and_resolves_paths(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True)

    sword = assets_dir / "sword.png"
    sword_alt = assets_dir / "sword_alt.png"
    sword.write_bytes(b"placeholder")
    sword_alt.write_bytes(b"placeholder")

    manifest_path = data_dir / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "name": "Iron Sword",
                    "template": "assets/sword.png",
                    "templates": ["assets/sword.png", "assets/sword_alt.png"],
                    "threshold": 0.82,
                    "info": "Melee weapon",
                }
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    item = items[0]
    assert item.item_id == "iron_sword"
    assert item.name == "Iron Sword"
    assert item.threshold == pytest.approx(0.82)
    assert item.info == "Melee weapon"
    assert item.template_paths == (sword.resolve(), sword_alt.resolve())


def test_load_items_clamps_threshold_and_skips_missing_template(tmp_path: Path) -> None:
    template_path = tmp_path / "icon.png"
    template_path.write_bytes(b"placeholder")

    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "id": "high_threshold",
                    "name": "High Threshold",
                    "template": "icon.png",
                    "threshold": 2.0,
                },
                {
                    "id": "missing_template",
                    "name": "Missing Template",
                    "template": "missing.png",
                },
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    assert items[0].item_id == "high_threshold"
    assert items[0].threshold == pytest.approx(0.99)


def test_load_items_raises_when_manifest_has_no_valid_items(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "id": "invalid",
                    "name": "Invalid Item",
                    "template": "does_not_exist.png",
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="No valid items found in manifest."):
        ItemRepository().load_items(manifest_path)
