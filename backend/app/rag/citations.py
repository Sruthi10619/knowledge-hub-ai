"""
Citation extractor and source matcher.
Extracts bracketed citations (e.g. [1], [2]) from LLM text and pairs them with source metadata.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set


class CitationExtractor:
    @staticmethod
    def extract_citations(text: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parses LLM response text for bracketed numbers, matches them with retrieved documents,
        and returns clean text + a dictionary of matched source citations.
        """
        # Find all brackets like [1], [2], [1][2], etc.
        pattern = r"\[(\d+)\]"
        matches: List[str] = re.findall(pattern, text)
        
        # Unique cited indices (1-indexed based on what we feed the LLM)
        cited_indices: Set[int] = {int(m) for m in matches}
        
        citations = {}
        for idx in cited_indices:
            # Check if this index exists in our retrieved docs (0-indexed)
            doc_idx = idx - 1
            if 0 <= doc_idx < len(retrieved_docs):
                doc = retrieved_docs[doc_idx]
                meta = doc["metadata"]
                
                citations[str(idx)] = {
                    "source": meta.get("source", "Unknown Document"),
                    "page": meta.get("page"),
                    "row": meta.get("row"),
                    "snippet": doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"],
                    "document_id": meta.get("document_id")
                }

        return {
            "text": text,
            "citations": citations
        }
