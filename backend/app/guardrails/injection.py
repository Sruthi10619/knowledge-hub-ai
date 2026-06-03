"""
Prompt injection and jailbreak detection logic.
"""

from __future__ import annotations

import re
from typing import List

# Common prompt injection patterns (heuristics)
INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"system\s+(?:override|bypass|reset)",
    r"you\s+are\s+now\s+(?:a|an)\s+unfiltered",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    r"developer\s+mode\s+(?:enabled|override)",
    r"forget\s+(?:your\s+)?rules",
    r"print\s+the\s+(?:system\s+)?prompt",
    r"reveal\s+your\s+(?:system\s+)?instructions",
    r"disregard\s+(?:the\s+)?above",
    r"new\s+rule:",
    r"override\s+system\s+prompt"
]


class InjectionDetector:
    @classmethod
    def detect(cls, text: str) -> bool:
        """
        Analyzes the text for known prompt injection / jailbreak patterns.
        Returns True if injection pattern is detected, False otherwise.
        """
        if not text:
            return False

        normalized_text = text.lower().strip()
        
        # Check against regex patterns
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, normalized_text):
                return True
                
        return False
