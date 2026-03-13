from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .models import ItemDefinition

LOGGER = logging.getLogger("overlay.items")


class ItemRepository:
    def load_items(self, manifest_path: Path) -> list[ItemDefinition]:
        manifest_path = manifest_path.expanduser().resolve()
        if not manifest_path.exists():
            raise FileNotFoundError(f"Item manifest not found: {manifest_path}")

        with manifest_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("Item manifest must contain an 'items' list.")

        items: list[ItemDefinition] = []
        for index, raw in enumerate(raw_items):
            item = self._parse_item(raw_item=raw, index=index)
            if item is not None:
                items.append(item)

        if not items:
            raise ValueError("No valid items found in manifest.")

        LOGGER.info("Loaded %d item definitions.", len(items))
        return items

    def _parse_item(
        self,
        raw_item: Any,
        index: int,
    ) -> ItemDefinition | None:
        if not isinstance(raw_item, dict):
            LOGGER.warning("Skipping item %d: expected object.", index)
            return None

        enabled_raw = raw_item.get("enabled", True)
        if isinstance(enabled_raw, bool):
            if not enabled_raw:
                return None
        elif enabled_raw is not None:
            LOGGER.warning(
                "Item %d has non-boolean 'enabled' value '%s'. Treating as enabled.",
                index,
                enabled_raw,
            )

        name = raw_item.get("name")
        if not isinstance(name, str) or not name.strip():
            LOGGER.warning("Skipping item %d: missing 'name'.", index)
            return None

        item_id = raw_item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            item_id = name.lower().strip().replace(" ", "_")

        info = raw_item.get("info")
        if not isinstance(info, str):
            info = ""

        return ItemDefinition(
            item_id=item_id,
            name=name,
            info=info,
        )
