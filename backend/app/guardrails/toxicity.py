"""
Toxicity scanner and keyword filter.
"""

from __future__ import annotations

import re
from typing import List

# Simple default toxicity word blocklist (can be expanded)
TOXIC_BLOCKLIST = [
    # Basic hate speech, slurs, extreme insults
    r"\bnigger\b", r"\bkike\b", r"\bfaggot\b", r"\bretard\b", r"\bchink\b"
]


class ToxicityScanner:
    @classmethod
    def contains_toxic_content(cls, text: str) -> bool:
        """
        Scans text for terms that violate the platform's toxicity policy.
        Returns True if toxic keywords are found, False otherwise.
        """
        if not text:
            return False

        normalized_text = text.lower().strip()
        
        # Check blocklist regexes
        for pattern in TOXIC_BLOCKLIST:
            if re.search(pattern, normalized_text):
                return True
                
        return False
