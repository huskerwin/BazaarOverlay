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


def test_load_items_with_enchantments(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "id": "sword",
                    "name": "Sword",
                    "info": "A sharp sword",
                    "enchantments": {
                        "golden": "Double value",
                        "heavy": "Slows twice as long",
                        "icy": "Freezes enemies",
                    },
                }
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    item = items[0]
    assert item.enchantments is not None
    assert item.enchantments["golden"] == "Double value"
    assert item.enchantments["heavy"] == "Slows twice as long"
    assert item.enchantments["icy"] == "Freezes enemies"


def test_load_items_with_all_12_enchantments(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    all_enchantments = {
        "golden": "Double value",
        "heavy": "Slows twice as long",
        "icy": "Freezes enemies",
        "turbo": "Hastes items",
        "shielded": "Gives shield",
        "restorative": "Heals",
        "toxic": "Poisons",
        "fiery": "Burns",
        "shiny": "Double damage and slow",
        "deadly": "+25% crit chance",
        "radiant": "Half freeze/slow",
        "obsidian": "Double damage",
    }
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "name": "Weapon",
                    "enchantments": all_enchantments,
                }
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    assert items[0].enchantments is not None
    assert len(items[0].enchantments) == 12
    assert items[0].enchantments == all_enchantments


def test_load_items_without_enchantments(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "name": "Simple Item",
                    "info": "No enchantments",
                }
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    assert items[0].enchantments is None


def test_load_items_invalid_enchantments_type(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "name": "Item",
                    "enchantments": "not a dict",
                }
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 1
    assert items[0].enchantments is None


def test_load_items_multiple_items_mixed_enchantments(tmp_path: Path) -> None:
    manifest_path = tmp_path / "items.json"
    _write_manifest(
        manifest_path,
        {
            "items": [
                {
                    "id": "item1",
                    "name": "Item One",
                    "enchantments": {"golden": "Value"},
                },
                {
                    "id": "item2",
                    "name": "Item Two",
                },
                {
                    "id": "item3",
                    "name": "Item Three",
                    "enchantments": {"heavy": "Slow"},
                },
            ]
        },
    )

    items = ItemRepository().load_items(manifest_path)

    assert len(items) == 3
    assert items[0].enchantments == {"golden": "Value"}
    assert items[1].enchantments is None
    assert items[2].enchantments == {"heavy": "Slow"}
