"""Shared search-hit → citation conversion for course and online sources."""

from __future__ import annotations

from typing import Literal

from app.modules.rag.models import Citation
from app.modules.rag.ports import SearchHit


def citation_from_hit(hit: SearchHit) -> Citation:
    source_type: Literal["course", "online"] = (
        "online" if hit.metadata.get("source_type") == "online" else "course"
    )
    title = hit.metadata.get("title")
    url = hit.metadata.get("url")
    safe_url = (
        str(url)
        if source_type == "online"
        and isinstance(url, str)
        and url.startswith("https://docs.python.org/")
        else None
    )
    return Citation(
        source_id=hit.source_id,
        chunk_id=hit.chunk_id,
        score=hit.score,
        source_type=source_type,
        source_title=str(title)[:200] if isinstance(title, str) else None,
        source_url=safe_url,
    )
