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


def test_load_items_generates_id_from_name(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "name": "Iron Sword",
                    "info": "A melee weapon",
                }
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    item = items[0]
    assert item.item_id == "iron_sword"
    assert item.name == "Iron Sword"
    assert item.info == "A melee weapon"
    assert item.template_paths == ()


def test_load_items_uses_explicit_id(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "id": "custom_id",
                    "name": "Custom Item",
                }
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    assert items[0].item_id == "custom_id"


def test_load_items_skips_disabled_entries(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "id": "disabled_item",
                    "name": "Disabled Item",
                    "enabled": False,
                },
                {
                    "id": "active_item",
                    "name": "Active Item",
                    "enabled": True,
                },
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    assert items[0].item_id == "active_item"


def test_load_items_skips_invalid_entries(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {"name": ""},
                {"name": "Valid Item"},
                {"no": "name field"},
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    assert items[0].name == "Valid Item"


def test_load_items_raises_when_manifest_empty(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(manifest_path, {"items": []})

    with pytest.raises(ValueError, match="No valid items found in manifest."):
        ItemRepository().load_items(manifest_path)


def test_load_items_raises_when_no_items_key(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(manifest_path, {})

    with pytest.raises(ValueError, match="Item manifest must contain an 'items' list."):
        ItemRepository().load_items(manifest_path)
