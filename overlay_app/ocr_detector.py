from __future__ import annotations

import logging
import re
from typing import TypedDict

import easyocr
import numpy as np


LOGGER = logging.getLogger("overlay.ocr_detector")


class OcrRegion(TypedDict):
    left: int
    top: int
    width: int
    height: int


class OcrItemDetector:
    def __init__(self, item_names: set[str]):
        self._item_names = {name.lower(): name for name in item_names}
        self._last_result: str | None = None
        self._reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    
    def detect_from_image(self, frame: np.ndarray, region: OcrRegion | None = None) -> str | None:
        if frame is None or frame.size == 0:
            return None
        
        try:
            if region:
                x, y = region["left"], region["top"]
                w, h = region["width"], region["height"]
                if x < 0 or y < 0 or w <= 0 or h <= 0:
                    return None
                if y + h > frame.shape[0] or x + w > frame.shape[1]:
                    return None
                crop = frame[y:y+h, x:x+w]
            else:
                crop = frame
            
            results = self._reader.readtext(crop, detail=0)
            
            if not results:
                return None
            
            text_results: list[str] = [str(r) for r in results]
            combined_text = ' '.join(text_results)
            cleaned = self._clean_text(combined_text)
            if not cleaned:
                return None
            
            match = self._find_best_match(cleaned)
            if match:
                self._last_result = match
                return match
            
            return None
            
        except Exception as exc:
            LOGGER.debug("OCR detection failed: %s", exc)
            return None
    
    def _clean_text(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^a-zA-Z0-9\'\s]', '', text)
        return text.strip()
    
    def _normalize_for_match(self, text: str) -> str:
        text = text.lower()
        text = text.replace("'", "")
        words = text.split()
        normalized_words = [w.rstrip('s') for w in words]
        return ' '.join(normalized_words)
    
    def _find_best_match(self, text: str) -> str | None:
        text_lower = text.lower()
        
        if text_lower in self._item_names:
            return self._item_names[text_lower]
        
        for name_lower, original_name in self._item_names.items():
            if name_lower in text_lower or text_lower in name_lower:
                return original_name
        
        text_no_apostrophe = text_lower.replace("'", "")
        for name_lower, original_name in self._item_names.items():
            name_no_apostrophe = name_lower.replace("'", "")
            if name_no_apostrophe in text_no_apostrophe or text_no_apostrophe in name_no_apostrophe:
                return original_name
        
        text_normalized = self._normalize_for_match(text_lower)
        for name_lower, original_name in self._item_names.items():
            name_no_apostrophe = name_lower.replace("'", "")
            name_normalized = self._normalize_for_match(name_no_apostrophe)
            if name_normalized in text_normalized or text_normalized in name_normalized:
                return original_name
        
        return None
    
    def get_last_result(self) -> str | None:
        return self._last_result
