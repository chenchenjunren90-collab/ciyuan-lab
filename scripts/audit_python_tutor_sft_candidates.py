"""Audit generated Python-tutor SFT candidates before MaaS export.

This performs a reproducibility and safety audit of all generated records.  It
is not represented as a substitute for a named educator's pedagogical review:
when ``--apply`` is used, the review queue explicitly records ``AI-AUDIT-V1``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from build_python_tutor_sft_candidates import (
    DEFAULT_OUTPUT_ROOT as V1_OUTPUT_ROOT,
)
from build_python_tutor_sft_candidates import (
    DEFAULT_PACK_ROOT,
    REPOSITORY_ROOT,
    build_records,
)
from build_python_tutor_sft_v2_candidates import (
    DEFAULT_OUTPUT_ROOT as V2_OUTPUT_ROOT,
)
from build_python_tutor_sft_v2_candidates import (
    build_records_v2,
)
from build_python_tutor_sft_v3_candidates import (
    DEFAULT_OUTPUT_ROOT as V3_OUTPUT_ROOT,
)
from build_python_tutor_sft_v3_candidates import (
    build_records_v3,
)
from validate_python_tutor_dataset import _read_jsonl, _validate_dataset, _validate_manifest

_VERSION_OUTPUT_ROOTS = {
    "v1": V1_OUTPUT_ROOT,
    "v2": V2_OUTPUT_ROOT,
    "v3": V3_OUTPUT_ROOT,
}

_FORBIDDEN_PATTERNS = (
    re.compile(r"隐藏测试|hidden test|api[_ -]?key|authorization\s*:\s*bearer", re.IGNORECASE),
    re.compile(r"```"),
)
_ROLE_LIMITS = {
    "teacher_explain": 220,
    "ta_misconception": 180,
    "ta_progressive_hint": 180,
    "peer_discussion": 160,
    "peer_debug": 160,
    "scope_refusal": 160,
    "test_boundary": 160,
    "peer_summary": 160,
    "safety_refusal": 220,
}
_ROLE_MARKERS = {
    "teacher_explain": ("Python 林老师",),
    "ta_misconception": ("Python 助教小程",),
    "ta_progressive_hint": ("Python 助教小程",),
    "peer_discussion": ("同伴小禾", "同学小禾"),
    "peer_debug": ("同伴阿拓", "同学阿拓"),
    "scope_refusal": ("Python 林老师",),
    "test_boundary": ("Python 助教小程",),
    "peer_summary": ("同学宁宁",),
    "safety_refusal": ("Python 林老师",),
}


def _read_review_queue(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "record_id",
            "category",
            "source_path",
            "question",
            "answer",
            "review_status",
            "reviewer_code",
            "review_note",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path}: missing required review columns")
        rows = [{key: (value or "") for key, value in row.items()} for row in reader]
    if not rows:
        raise ValueError(f"{path}: no review rows")
    return rows


def _record_fields(record: Mapping[str, Any]) -> tuple[str, str, str, str]:
    conversations = record.get("conversations")
    if not isinstance(conversations, list) or len(conversations) != 3:
        raise ValueError("candidate has invalid conversations")
    system, user, assistant = conversations
    if not all(isinstance(turn, dict) for turn in (system, user, assistant)):
        raise ValueError("candidate has invalid turns")
    system_text = system.get("value")
    user_text = user.get("value")
    assistant_text = assistant.get("value")
    if not all(isinstance(item, str) for item in (system_text, user_text, assistant_text)):
        raise ValueError("candidate turn content must be text")
    user_payload = json.loads(user_text)
    assistant_payload = json.loads(assistant_text)
    if not isinstance(user_payload, dict) or not isinstance(assistant_payload, dict):
        raise ValueError("candidate payload must be an object")
    question = user_payload.get("question")
    answer = assistant_payload.get("answer")
    if not isinstance(question, str) or not isinstance(answer, str):
        raise ValueError("candidate question and answer must be text")
    return system_text, question, answer, assistant_text


def _audit(
    *,
    records: Sequence[Mapping[str, Any]],
    manifest: Sequence[Mapping[str, Any]],
    review_rows: Sequence[Mapping[str, str]],
    expected_records: Sequence[Mapping[str, Any]],
    expected_manifest: Sequence[Mapping[str, Any]],
    reviewer_code: str,
) -> dict[str, object]:
    _validate_dataset(records)
    _validate_manifest(manifest, len(records))
    if list(records) != list(expected_records):
        raise ValueError(
            "candidate dataset does not reproduce from the checked-in Python course pack"
        )
    if list(manifest) != list(expected_manifest):
        raise ValueError(
            "candidate manifest does not reproduce from the checked-in Python course pack"
        )
    if len(review_rows) != len(records):
        raise ValueError("review queue and candidate record counts differ")

    findings: list[str] = []
    for index, (record, item, review) in enumerate(
        zip(records, manifest, review_rows, strict=True), start=1
    ):
        record_id = item.get("record_id")
        category = item.get("category")
        if not isinstance(record_id, str) or not isinstance(category, str):
            raise ValueError(f"record {index}: invalid manifest fields")
        if category not in _ROLE_LIMITS:
            raise ValueError(f"{record_id}: unsupported category {category}")
        system, question, answer, assistant_text = _record_fields(record)
        if record_id != review.get("record_id"):
            raise ValueError(f"{record_id}: review queue record order differs")
        if category != review.get("category"):
            raise ValueError(f"{record_id}: review queue category differs")
        if question != review.get("question") or answer != review.get("answer"):
            raise ValueError(f"{record_id}: review queue content differs from training record")
        review_status = review.get("review_status", "")
        if review_status not in {"pending_human_review", "approved"}:
            raise ValueError(
                f"{record_id}: review queue has unexpected review_status {review_status!r}"
            )
        if review_status == "approved" and not review.get("reviewer_code", "").strip():
            raise ValueError(f"{record_id}: approved review row is missing a reviewer_code")
        if not any(marker in system for marker in _ROLE_MARKERS[category]):
            findings.append(f"{record_id}: missing role marker")
        if len(answer) > _ROLE_LIMITS[category]:
            findings.append(f"{record_id}: answer exceeds {category} limit")
        if "。。" in answer:
            findings.append(f"{record_id}: duplicated full stop")
        joined = "\n".join((system, question, answer, assistant_text))
        if any(pattern.search(joined) for pattern in _FORBIDDEN_PATTERNS):
            findings.append(f"{record_id}: forbidden marker or code fence")
    if findings:
        raise ValueError("audit failed: " + "; ".join(findings[:8]))
    return {
        "audit_type": "template_reproducibility_and_safety",
        "reviewer_code": reviewer_code,
        "records_checked": len(records),
        "categories_checked": sorted(_ROLE_LIMITS),
        "automatic_checks": [
            "ShareGPT schema and JSON citation contract",
            "exact reproduction from checked-in Python course sources",
            "review queue matches training records",
            "role marker and role-specific answer length",
            "no code fence, hidden-test, credential-shaped or authorization marker",
            "no duplicated Chinese full stop",
        ],
        "limitations": [
            "This record is an AI audit, not a named educator signature.",
            "A course teacher should still review classroom usefulness before competition "
            "submission.",
        ],
    }


def _apply_ai_review(path: Path, rows: Sequence[Mapping[str, str]], reviewer_code: str) -> None:
    changed_by_other_reviewer = [
        row["record_id"]
        for row in rows
        if row["reviewer_code"] not in {"", reviewer_code}
        or row["review_status"] not in {"pending_human_review", "approved"}
    ]
    if changed_by_other_reviewer:
        raise ValueError(
            "refusing to overwrite existing non-AI reviews: "
            + ", ".join(changed_by_other_reviewer[:5])
        )
    fieldnames = tuple(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "review_status": "approved",
                    "reviewer_code": reviewer_code,
                    "review_note": (
                        f"{reviewer_code}: source replay, schema/citation, role, length and "
                        "boundary checks passed."
                    ),
                }
            )


_AI_AUDIT_PREFIX = "AI-AUDIT-"


def _queue_decision(rows: Sequence[Mapping[str, str]]) -> str:
    """Classify the review queue's current on-disk approval state."""
    if not rows:
        return "empty"
    statuses = {row.get("review_status", "") for row in rows}
    if statuses == {"approved"}:
        if all((row.get("reviewer_code") or "").startswith(_AI_AUDIT_PREFIX) for row in rows):
            return "approved_by_ai_audit"
        return "approved_by_reviewer"
    if statuses == {"pending_human_review"}:
        return "pending_human_review"
    return "mixed_review_states"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Python tutor SFT candidates")
    parser.add_argument("--candidate-root", type=Path, default=None)
    parser.add_argument("--pack-root", type=Path, default=DEFAULT_PACK_ROOT)
    parser.add_argument("--source-version", choices=("v1", "v2", "v3"), default="v1")
    parser.add_argument("--apply", action="store_true", help="Record the AI audit as approved rows")
    args = parser.parse_args()
    root = (args.candidate_root or _VERSION_OUTPUT_ROOTS[args.source_version]).resolve()
    try:
        dataset_name = f"sharegpt-python-tutor-{args.source_version}.jsonl"
        record_builders = {"v1": build_records, "v2": build_records_v2, "v3": build_records_v3}
        record_builder = record_builders[args.source_version]
        reviewer_code = f"AI-AUDIT-{args.source_version.upper()}"
        records = _read_jsonl(root / dataset_name)
        manifest = _read_jsonl(root / "review-manifest.jsonl")
        review_path = root / "review-queue.csv"
        review_rows = _read_review_queue(review_path)
        expected_records, expected_manifest = record_builder(args.pack_root.resolve())
        report = _audit(
            records=records,
            manifest=manifest,
            review_rows=review_rows,
            expected_records=expected_records,
            expected_manifest=expected_manifest,
            reviewer_code=reviewer_code,
        )
        report_path = root / "ai-audit-report.json"
        if args.apply:
            _apply_ai_review(review_path, review_rows, reviewer_code)
        # Report the queue's actual on-disk state so the decision cannot drift
        # from what a later export would read.
        final_rows = _read_review_queue(review_path)
        report["decision"] = _queue_decision(final_rows)
        report["review_queue"] = review_path.relative_to(REPOSITORY_ROOT).as_posix()
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({**report, "report": report_path.name}, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as error:
        print(f"not audited: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
