"""Deterministic offline embeddings for repeatable MVP retrieval tests."""

from __future__ import annotations

import hashlib
import math

from app.modules.rag.retriever import tokenize


class TokenHashEmbedder:
    """Map lexical tokens to a fixed vector without claiming semantic embeddings.

    This keeps the pgvector path runnable offline. A production embedding provider can
    replace it behind the same ``embed`` method after its model and data policy are approved.
    """

    def __init__(self, dimensions: int = 384) -> None:
        if dimensions < 16:
            raise ValueError("dimensions must be at least 16")
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token, count in tokenize(text).items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign * float(count)
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector
