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
    orb_descriptors: np.ndarray | None
    orb_keypoint_count: int


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

        self._center_bias_weight = float(max(0.0, min(0.60, config.center_bias_weight)))
        self._base_score_weight = 1.0 - self._center_bias_weight

        self._shortlist_size = max(1, int(config.shortlist_size))
        self._orb_weight = float(max(0.0, min(1.0, config.orb_weight)))
        self._template_weight = 1.0 - self._orb_weight
        self._orb_ratio_test = float(max(0.50, min(0.95, config.orb_ratio_test)))
        self._orb_min_good_matches = max(1, int(config.orb_min_good_matches))

        self._orb = cv2.ORB.create(400)
        self._bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        self._variants = self._load_variants(items)
        if not self._variants:
            raise ValueError("No readable template images were loaded.")

        self._max_template_width = max(variant.gray.shape[1] for variant in self._variants)
        self._max_template_height = max(variant.gray.shape[0] for variant in self._variants)

        LOGGER.info(
            "Template matcher ready with %d variants across %d items (shortlist=%d, orb_weight=%.2f).",
            len(self._variants),
            len({variant.item.item_id for variant in self._variants}),
            self._shortlist_size,
            self._orb_weight,
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

        roi_descriptors, roi_keypoint_count = self._compute_orb_descriptors(roi_gray)

        stage_one_best: dict[str, tuple[float, TemplateVariant]] = {}
        for variant in self._variants:
            template_score = self._score_variant_template(roi_gray, roi_edges, variant)
            if template_score is None:
                continue

            current = stage_one_best.get(variant.item.item_id)
            if current is None or template_score > current[0]:
                stage_one_best[variant.item.item_id] = (template_score, variant)

        if not stage_one_best:
            return MatchResult(
                matched=False,
                confidence=0.0,
                threshold=self._config.global_threshold,
                item=None,
                best_item=None,
                message="No template fits the current capture size.",
            )

        shortlisted = sorted(
            stage_one_best.values(),
            key=lambda entry: entry[0],
            reverse=True,
        )[: self._shortlist_size]

        best_variant: TemplateVariant | None = None
        best_score = -1.0

        for template_score, variant in shortlisted:
            orb_score = self._orb_score_for_variant(
                variant,
                roi_descriptors,
                roi_keypoint_count,
            )
            final_score = self._blend_scores(template_score=template_score, orb_score=orb_score)
            if final_score > best_score:
                best_score = final_score
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


    def _blend_scores(self, template_score: float, orb_score: float | None) -> float:
        if orb_score is None or self._orb_weight <= 0.0:
            return template_score
        return (self._template_weight * template_score) + (self._orb_weight * orb_score)

    def _score_variant_template(
        self,
        roi_gray: np.ndarray,
        roi_edges: np.ndarray,
        variant: TemplateVariant,
    ) -> float | None:
        gray_score, gray_loc = self._max_score(roi_gray, variant.gray)
        if gray_score < 0:
            return None

        edge_score, _edge_loc = self._max_score(roi_edges, variant.edges)
        if edge_score < 0:
            edge_score = gray_score

        base_score = (self._gray_weight * gray_score) + (self._edge_weight * edge_score)
        center_score = self._center_proximity_score(
            roi_shape=roi_gray.shape,
            match_loc=gray_loc,
            template_shape=variant.gray.shape,
        )
        return (self._base_score_weight * base_score) + (self._center_bias_weight * center_score)

    @staticmethod
    def _center_proximity_score(
        roi_shape: tuple[int, ...],
        match_loc: tuple[int, int],
        template_shape: tuple[int, ...],
    ) -> float:
        roi_height, roi_width = roi_shape[:2]
        tpl_height, tpl_width = template_shape[:2]

        match_center_x = float(match_loc[0]) + (float(tpl_width) / 2.0)
        match_center_y = float(match_loc[1]) + (float(tpl_height) / 2.0)

        roi_center_x = float(roi_width) / 2.0
        roi_center_y = float(roi_height) / 2.0

        dx = (match_center_x - roi_center_x) / max(1.0, roi_center_x)
        dy = (match_center_y - roi_center_y) / max(1.0, roi_center_y)
        distance = math.sqrt((dx * dx) + (dy * dy))
        return max(0.0, 1.0 - min(1.0, distance))

    def _orb_score_for_variant(
        self,
        variant: TemplateVariant,
        roi_descriptors: np.ndarray | None,
        roi_keypoint_count: int,
    ) -> float | None:
        if self._orb_weight <= 0.0:
            return None

        template_descriptors = variant.orb_descriptors
        if template_descriptors is None or roi_descriptors is None:
            return None

        if (
            variant.orb_keypoint_count < self._orb_min_good_matches
            or roi_keypoint_count < self._orb_min_good_matches
        ):
            return None

        if len(template_descriptors) < 2 or len(roi_descriptors) < 2:
            return None

        try:
            raw_matches = self._bf_matcher.knnMatch(template_descriptors, roi_descriptors, k=2)
        except cv2.error:
            return None

        good_matches = 0
        for pair in raw_matches:
            if len(pair) < 2:
                continue
            first, second = pair
            if first.distance < (self._orb_ratio_test * second.distance):
                good_matches += 1

        if good_matches <= 0:
            return 0.0

        normalizer = max(
            self._orb_min_good_matches,
            min(variant.orb_keypoint_count, roi_keypoint_count),
        )
        return min(1.0, float(good_matches) / float(normalizer))

    def _compute_orb_descriptors(self, image: np.ndarray) -> tuple[np.ndarray | None, int]:
        keypoints, descriptors = self._orb.detectAndCompute(image, None)
        return descriptors, len(keypoints)


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
                    descriptors, keypoint_count = self._compute_orb_descriptors(resized)
                    variants.append(
                        TemplateVariant(
                            item=item,
                            source_path=template_path,
                            scale=scale,
                            gray=resized,
                            edges=edges,
                            orb_descriptors=descriptors,
                            orb_keypoint_count=keypoint_count,
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
    def _max_score(
        search_image: np.ndarray,
        template_image: np.ndarray,
    ) -> tuple[float, tuple[int, int]]:
        if (
            search_image.shape[0] < template_image.shape[0]
            or search_image.shape[1] < template_image.shape[1]
        ):
            return -1.0, (0, 0)

        result = cv2.matchTemplate(search_image, template_image, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return float(max_val), (int(max_loc[0]), int(max_loc[1]))
