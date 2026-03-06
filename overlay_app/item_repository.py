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
            item = self._parse_item(raw_item=raw, index=index, manifest_path=manifest_path)
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
        manifest_path: Path,
    ) -> ItemDefinition | None:
        if not isinstance(raw_item, dict):
            LOGGER.warning("Skipping item %d: expected object.", index)
            return None

        enabled_raw = raw_item.get("enabled", True)
        if isinstance(enabled_raw, bool):
            if not enabled_raw:
                LOGGER.info("Skipping disabled item at index %d.", index)
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

        raw_templates = self._extract_template_entries(raw_item)
        resolved_templates: list[Path] = []
        for raw_path in raw_templates:
            resolved = self._resolve_template_path(raw_path, manifest_path)
            if resolved.exists() and resolved.is_file():
                resolved_templates.append(resolved)
            else:
                LOGGER.warning(
                    "Item '%s' template does not exist: %s", name, resolved.as_posix()
                )

        if not resolved_templates:
            LOGGER.warning("Skipping item '%s': no valid template images.", name)
            return None

        threshold = self._parse_threshold(raw_item.get("threshold"), name)
        info = raw_item.get("info")
        if not isinstance(info, str):
            info = ""

        return ItemDefinition(
            item_id=item_id,
            name=name,
            template_paths=tuple(resolved_templates),
            info=info,
            threshold=threshold,
        )

    @staticmethod
    def _extract_template_entries(raw_item: dict[str, Any]) -> list[str]:
        templates: list[str] = []

        single = raw_item.get("template")
        if isinstance(single, str) and single.strip():
            templates.append(single.strip())

        many = raw_item.get("templates")
        if isinstance(many, str) and many.strip():
            templates.append(many.strip())
        elif isinstance(many, list):
            for value in many:
                if isinstance(value, str) and value.strip():
                    templates.append(value.strip())

        deduped = list(dict.fromkeys(templates))
        return deduped

    @staticmethod
    def _resolve_template_path(raw_path: str, manifest_path: Path) -> Path:
        candidate = Path(raw_path).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()

        manifest_dir = manifest_path.parent
        project_dir = manifest_dir.parent

        candidates = [
            (manifest_dir / candidate).resolve(),
            (project_dir / candidate).resolve(),
        ]

        for resolved in candidates:
            if resolved.exists():
                return resolved

        return candidates[0]

    @staticmethod
    def _parse_threshold(raw_value: Any, item_name: str) -> float | None:
        if raw_value is None:
            return None

        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            LOGGER.warning(
                "Item '%s' has invalid threshold '%s'. Using global default.",
                item_name,
                raw_value,
            )
            return None

        if value < 0.05 or value > 0.99:
            LOGGER.warning(
                "Item '%s' threshold %.3f is outside [0.05, 0.99]. Clamping.",
                item_name,
                value,
            )
            value = max(0.05, min(0.99, value))

        return value
