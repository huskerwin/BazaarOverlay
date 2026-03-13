"""
OCR-based item detection using EasyOCR.

Extracts text from a configurable region and matches against known item names.
"""

from __future__ import annotations

import logging
import re
from typing import TypedDict

import easyocr
import numpy as np


LOGGER = logging.getLogger("overlay.ocr_detector")


class OcrRegion(TypedDict):
    """OCR region definition relative to captured ROI."""
    left: int
    top: int
    width: int
    height: int


class OcrItemDetector:
    """
    OCR-based item detector using EasyOCR.
    
    Extracts text from game UI and matches against item names from database.
    Supports fuzzy matching for OCR errors and common variations.
    """
    
    # Words that commonly cause false matches - require complete word match
    BLACKLIST = {"damage"}
    
    def __init__(self, item_names: set[str]):
        """
        Initialize OCR detector with known item names.
        
        Args:
            item_names: Set of item names to match against
        """
        # Map lowercase names to original for case-insensitive matching
        self._item_names = {name.lower(): name for name in item_names}
        self._last_result: str | None = None
        self._last_detected_text: str | None = None
        
        # Initialize EasyOCR reader (loads model on first use)
        # gpu=False uses CPU, set to True for GPU acceleration
        self._reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    
    @property
    def last_detected_text(self) -> str | None:
        """Returns the last detected text from OCR."""
        return self._last_detected_text
    
    def detect_from_image(self, frame: np.ndarray, region: OcrRegion | None = None) -> str | None:
        """
        Detect item name from image frame using OCR.
        
        Args:
            frame: BGR image data from screen capture
            region: Optional region to crop before OCR
            
        Returns:
            Matched item name or None if no match
        """
        if frame is None or frame.size == 0:
            return None
        
        try:
            # Crop to OCR region if specified and valid
            crop = frame
            if region:
                x = region.get("left", 0)
                y = region.get("top", 0)
                w = region.get("width", 0)
                h = region.get("height", 0)
                
                # Use full frame if region is not valid
                if w > 0 and h > 0 and x >= 0 and y >= 0:
                    if y + h <= frame.shape[0] and x + w <= frame.shape[1]:
                        crop = frame[y:y+h, x:x+w]
            
            # Run EasyOCR on the cropped region
            results = self._reader.readtext(crop, detail=0)
            
            if not results:
                LOGGER.info("OCR: No text detected")
                return None
            
            # Combine all detected text
            text_results: list[str] = [str(r) for r in results]
            combined_text = ' '.join(text_results)
            LOGGER.info("OCR raw text: '%s'", combined_text)
            
            # Clean and normalize text
            cleaned = self._clean_text(combined_text)
            LOGGER.info("OCR cleaned text: '%s'", cleaned)
            
            # Store for later retrieval
            self._last_detected_text = cleaned
            
            if not cleaned:
                return None
            
            # Try to match against known items
            match = self._find_best_match(cleaned)
            if match:
                LOGGER.info("OCR matched to: '%s'", match)
                self._last_result = match
                return match
            
            LOGGER.info("OCR: No match found for '%s'", cleaned)
            return None
            
        except Exception as exc:
            LOGGER.debug("OCR detection failed: %s", exc)
            return None
    
    def _clean_text(self, text: str) -> str:
        """
        Clean OCR output for matching.
        
        - Strips whitespace
        - Normalizes spaces
        - Removes special characters
        """
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[^a-zA-Z0-9\'\s]', '', text)  # Keep only alphanumeric
        return text.strip()
    
    def _normalize_for_match(self, text: str) -> str:
        """
        Normalize text for fuzzy matching.
        
        - Lowercase
        - Remove apostrophes
        - Remove trailing 's' for plural handling
        """
        text = text.lower()
        text = text.replace("'", "")
        words = text.split()
        normalized_words = [w.rstrip('s') for w in words]
        return ' '.join(normalized_words)
    
    def _find_best_match(self, text: str) -> str | None:
        """
        Find best matching item name for OCR text.
        
        Tries multiple matching strategies:
        1. Exact match (case-insensitive)
        2. Word match (item name as standalone word in text)
        3. Contains match (skip if detected text is blacklisted)
        4. Apostrophe-insensitive match (skip if blacklisted)
        5. Fuzzy normalized match (skip if blacklisted)
        """
        text_lower = text.lower()
        text_words = set(re.findall(r'\b[a-z]+\b', text_lower))
        has_blacklist_word = bool(text_words & self.BLACKLIST)
        
        # 1. Exact match (always allowed)
        if text_lower in self._item_names:
            return self._item_names[text_lower]
        
        # 2. Word match - check if any item name appears as a standalone word
        for name_lower, original_name in self._item_names.items():
            if name_lower in text_words:
                return original_name
        
        # 3. Contains match (skip if blacklisted)
        if not has_blacklist_word:
            for name_lower, original_name in self._item_names.items():
                if name_lower in text_lower or text_lower in name_lower:
                    return original_name
        
        # 4. Apostrophe-insensitive match (skip if blacklisted)
        if not has_blacklist_word:
            text_no_apostrophe = text_lower.replace("'", "")
            for name_lower, original_name in self._item_names.items():
                name_no_apostrophe = name_lower.replace("'", "")
                if name_no_apostrophe in text_no_apostrophe or text_no_apostrophe in name_no_apostrophe:
                    return original_name
        
        # 5. Fuzzy normalized match (skip if blacklisted)
        if not has_blacklist_word:
            text_normalized = self._normalize_for_match(text_lower)
            for name_lower, original_name in self._item_names.items():
                name_no_apostrophe = name_lower.replace("'", "")
                name_normalized = self._normalize_for_match(name_no_apostrophe)
                if name_normalized in text_normalized or text_normalized in name_normalized:
                    return original_name
        
        if has_blacklist_word:
            LOGGER.info("OCR: Skipped matches due to blacklisted word in '%s'", text)
        
        return None
    
    def get_last_result(self) -> str | None:
        """Returns the last matched item name."""
        return self._last_result
