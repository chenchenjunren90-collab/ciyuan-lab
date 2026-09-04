"""Validate the review-only Python SFT dataset before any MaaS upload."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPOSITORY_ROOT / "training" / "python_tutor" / "v1" / "candidates"
_SECRET_PATTERN = re.compile(r"(?:ak|sk|api[_-]?key)[-_=:][A-Za-z0-9_+/=-]{8,}", re.IGNORECASE)
_FORBIDDEN_MARKERS = ("隐藏测试", "hidden test", "authorization: bearer")
_EXPECTED_SPEAKERS = ("system", "human", "gpt")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{number}: invalid JSON") from error
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: each record must be an object")
        rows.append(value)
    if not rows:
        raise ValueError(f"{path}: no records")
    return rows


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected a non-empty string")
    return value


def _validate_dataset(records: Sequence[Mapping[str, Any]]) -> Counter[str]:
    categories: Counter[str] = Counter()
    seen_serialized: set[str] = set()
    for index, record in enumerate(records, start=1):
        conversations = record.get("conversations")
        if not isinstance(conversations, list) or len(conversations) != 3:
            raise ValueError(f"record {index}: expected exactly three conversations")
        speakers: list[str] = []
        values: list[str] = []
        for turn_index, turn in enumerate(conversations, start=1):
            if not isinstance(turn, dict):
                raise ValueError(f"record {index}, turn {turn_index}: expected object")
            speaker_label = f"record {index}, turn {turn_index}.from"
            value_label = f"record {index}, turn {turn_index}.value"
            speakers.append(_require_string(turn.get("from"), speaker_label))
            values.append(_require_string(turn.get("value"), value_label))
        if tuple(speakers) != _EXPECTED_SPEAKERS:
            raise ValueError(f"record {index}: expected speaker order {_EXPECTED_SPEAKERS}")
        joined = "\n".join(values)
        lowered = joined.lower()
        has_forbidden_marker = any(marker in lowered for marker in _FORBIDDEN_MARKERS)
        if _SECRET_PATTERN.search(joined) or has_forbidden_marker:
            raise ValueError(
                f"record {index}: contains a secret-shaped value or forbidden test marker"
            )
        try:
            user_payload = json.loads(values[1])
            assistant_payload = json.loads(values[2])
        except json.JSONDecodeError as error:
            raise ValueError(
                f"record {index}: human and gpt content must be JSON objects"
            ) from error
        if not isinstance(user_payload, dict) or not isinstance(assistant_payload, dict):
            raise ValueError(f"record {index}: human and gpt content must be JSON objects")
        evidence = user_payload.get("evidence")
        valid_question = isinstance(user_payload.get("question"), str)
        if not valid_question or not isinstance(evidence, list) or not evidence:
            raise ValueError(f"record {index}: missing question or evidence")
        chunk_ids = {
            item.get("chunk_id")
            for item in evidence
            if isinstance(item, dict) and isinstance(item.get("chunk_id"), str)
        }
        citations = assistant_payload.get("citation_chunk_ids")
        if set(assistant_payload) != {"answer", "citation_chunk_ids"}:
            raise ValueError(
                f"record {index}: assistant schema must contain answer and citation_chunk_ids"
            )
        if not isinstance(assistant_payload.get("answer"), str) or not isinstance(citations, list):
            raise ValueError(f"record {index}: invalid assistant schema")
        valid_citations = citations and all(
            isinstance(item, str) and item in chunk_ids for item in citations
        )
        if not valid_citations:
            raise ValueError(f"record {index}: citation must reference supplied evidence")
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if serialized in seen_serialized:
            raise ValueError(f"record {index}: duplicate record")
        seen_serialized.add(serialized)
        role = values[0]
        if "林老师" in role:
            categories["teacher"] += 1
        elif "助教小程" in role:
            categories["ta"] += 1
        elif "阿拓" in role:
            categories["debug_peer"] += 1
        else:
            categories["peer"] += 1
    return categories


def _validate_manifest(
    manifest: Sequence[Mapping[str, Any]],
    expected_count: int,
    *,
    expected_status: str = "pending_human_review",
) -> Counter[str]:
    if len(manifest) != expected_count:
        raise ValueError("manifest and dataset record counts differ")
    record_ids: set[str] = set()
    categories: Counter[str] = Counter()
    for index, item in enumerate(manifest, start=1):
        record_id = _require_string(item.get("record_id"), f"manifest {index}.record_id")
        if record_id in record_ids:
            raise ValueError(f"manifest {index}: duplicate record id")
        record_ids.add(record_id)
        if item.get("review_status") != expected_status:
            raise ValueError(f"manifest {index}: review status must be {expected_status!r}")
        category = _require_string(item.get("category"), f"manifest {index}.category")
        categories[category] += 1
    return categories


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Python tutor SFT candidates")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_ROOT / "sharegpt-python-tutor-v1.jsonl",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_ROOT / "review-manifest.jsonl")
    parser.add_argument(
        "--review-status",
        default="pending_human_review",
        choices=("pending_human_review", "approved"),
        help="Expected review_status for every manifest row",
    )
    args = parser.parse_args()
    dataset = _read_jsonl(args.dataset)
    manifest = _read_jsonl(args.manifest)
    role_counts = _validate_dataset(dataset)
    category_counts = _validate_manifest(
        manifest, len(dataset), expected_status=args.review_status
    )
    print(
        json.dumps(
            {
                "records": len(dataset),
                "roles": dict(sorted(role_counts.items())),
                "categories": dict(sorted(category_counts.items())),
                "review_status": args.review_status,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
