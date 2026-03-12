from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.ocr_detector import OcrItemDetector, OcrRegion


@pytest.fixture
def sample_item_names() -> set[str]:
    return {
        "Sword",
        "Shield",
        "Potion",
        "Health Potion",
        "Mana Potion",
        "Iron Sword",
        "Golden Apple",
        "Dragon's Breath",
    }


@pytest.fixture
def ocr_detector(sample_item_names) -> OcrItemDetector:
    return OcrItemDetector(sample_item_names)


def test_ocr_detector_exact_match(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "Sword", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    result = ocr_detector.detect_from_image(frame)
    
    assert result == "Sword"


def test_ocr_detector_partial_match(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "Iron Sword", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    result = ocr_detector.detect_from_image(frame)
    
    assert result == "Iron Sword"


def test_ocr_detector_no_match(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "Unknown Item", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    result = ocr_detector.detect_from_image(frame)
    
    assert result is None


def test_ocr_detector_empty_frame(ocr_detector: OcrItemDetector) -> None:
    result = ocr_detector.detect_from_image(np.array([]))
    
    assert result is None


def test_ocr_detector_none_frame(ocr_detector: OcrItemDetector) -> None:
    result = ocr_detector.detect_from_image(None)
    
    assert result is None


def test_ocr_detector_with_region(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "Potion", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    region: OcrRegion = {"left": 10, "top": 30, "width": 100, "height": 40}
    result = ocr_detector.detect_from_image(frame, region)
    
    assert result is not None


def test_ocr_detector_invalid_region(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    
    region: OcrRegion = {"left": 500, "top": 500, "width": 100, "height": 40}
    result = ocr_detector.detect_from_image(frame, region)
    
    assert result is None


def test_ocr_detector_get_last_result(ocr_detector: OcrItemDetector) -> None:
    assert ocr_detector.get_last_result() is None
    
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "Shield", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    ocr_detector.detect_from_image(frame)
    
    assert ocr_detector.get_last_result() == "Shield"


def test_ocr_detector_case_insensitive(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "health potion", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    result = ocr_detector.detect_from_image(frame)
    
    assert result == "Health Potion"


def test_ocr_detector_contains_match(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "Dragon Breath", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    result = ocr_detector.detect_from_image(frame)
    
    assert result == "Dragon's Breath"


def test_ocr_detector_apostrophe_handling(ocr_detector: OcrItemDetector) -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    import cv2
    cv2.putText(frame, "Dragons Breath", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    result = ocr_detector.detect_from_image(frame)
    
    assert result == "Dragon's Breath"
