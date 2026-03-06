from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .config import MatchConfig
from .models import ItemDefinition, MatchResult

LOGGER = logging.getLogger("overlay.matcher")


@dataclass(frozen=True)
class TemplateVariant:
    item: ItemDefinition
    source_path: Path
    scale: float
    gray: np.ndarray
    edges: np.ndarray


class TemplateMatcher:
    def __init__(self, items: list[ItemDefinition], config: MatchConfig):
        self._config = config

        total_weight = config.gray_weight + config.edge_weight
        if total_weight <= 0:
            self._gray_weight = 1.0
            self._edge_weight = 0.0
        else:
            self._gray_weight = config.gray_weight / total_weight
            self._edge_weight = config.edge_weight / total_weight

        self._variants = self._load_variants(items)
        if not self._variants:
            raise ValueError("No readable template images were loaded.")

        self._max_template_width = max(variant.gray.shape[1] for variant in self._variants)
        self._max_template_height = max(variant.gray.shape[0] for variant in self._variants)

        LOGGER.info(
            "Template matcher ready with %d variants across %d items.",
            len(self._variants),
            len({variant.item.item_id for variant in self._variants}),
        )

    @property
    def minimum_roi_radius(self) -> int:
        max_dimension = max(self._max_template_width, self._max_template_height)
        return max(24, int(math.ceil(max_dimension / 2.0)) + 6)

    def match(self, roi_bgr: np.ndarray) -> MatchResult:
        if roi_bgr.size == 0:
            return MatchResult(
                matched=False,
                confidence=0.0,
                threshold=self._config.global_threshold,
                item=None,
                best_item=None,
                message="Empty capture region.",
            )

        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        roi_gray = cv2.equalizeHist(roi_gray)
        roi_edges = cv2.Canny(roi_gray, 60, 150)

        best_variant: TemplateVariant | None = None
        best_score = -1.0

        for variant in self._variants:
            gray_score = self._max_score(roi_gray, variant.gray)
            if gray_score < 0:
                continue

            edge_score = self._max_score(roi_edges, variant.edges)
            if edge_score < 0:
                edge_score = gray_score

            combined = (self._gray_weight * gray_score) + (self._edge_weight * edge_score)
            if combined > best_score:
                best_score = combined
                best_variant = variant

        if best_variant is None:
            return MatchResult(
                matched=False,
                confidence=0.0,
                threshold=self._config.global_threshold,
                item=None,
                best_item=None,
                message="No template fits the current capture size.",
            )

        threshold = best_variant.item.threshold
        if threshold is None:
            threshold = self._config.global_threshold

        matched = best_score >= threshold
        if matched:
            message = best_variant.item.info or f"Matched '{best_variant.item.name}'."
            return MatchResult(
                matched=True,
                confidence=best_score,
                threshold=threshold,
                item=best_variant.item,
                best_item=best_variant.item,
                message=message,
            )

        return MatchResult(
            matched=False,
            confidence=best_score,
            threshold=threshold,
            item=None,
            best_item=best_variant.item,
            message="No confident match found.",
        )

    def _load_variants(self, items: list[ItemDefinition]) -> list[TemplateVariant]:
        variants: list[TemplateVariant] = []

        for item in items:
            for template_path in item.template_paths:
                image = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                if image is None:
                    LOGGER.warning(
                        "Failed to read template '%s' for item '%s'.",
                        template_path.as_posix(),
                        item.name,
                    )
                    continue

                image = cv2.equalizeHist(image)
                for scale in self._config.scales:
                    resized = self._resize_template(image, scale)
                    if resized is None:
                        continue

                    edges = cv2.Canny(resized, 60, 150)
                    variants.append(
                        TemplateVariant(
                            item=item,
                            source_path=template_path,
                            scale=scale,
                            gray=resized,
                            edges=edges,
                        )
                    )

        return variants

    @staticmethod
    def _resize_template(image: np.ndarray, scale: float) -> np.ndarray | None:
        if scale <= 0:
            return None

        if abs(scale - 1.0) < 1e-6:
            resized = image
        else:
            width = int(round(image.shape[1] * scale))
            height = int(round(image.shape[0] * scale))
            if width < 6 or height < 6:
                return None
            resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)

        if resized.shape[0] < 6 or resized.shape[1] < 6:
            return None
        return resized

    @staticmethod
    def _max_score(search_image: np.ndarray, template_image: np.ndarray) -> float:
        if (
            search_image.shape[0] < template_image.shape[0]
            or search_image.shape[1] < template_image.shape[1]
        ):
            return -1.0

        result = cv2.matchTemplate(search_image, template_image, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return float(max_val)
