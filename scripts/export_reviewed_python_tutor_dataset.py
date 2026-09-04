"""Export only human-approved Python SFT records for MaaS upload."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_ROOT = REPOSITORY_ROOT / "training" / "python_tutor" / "v1" / "candidates"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "training" / "python_tutor" / "v1" / "approved"

# Machine audits may approve data for further human review, but they are not a
# named educator signature. Records approved only by an AI audit must not be
# exported as "human-approved" for MaaS upload.
_AI_AUDIT_PREFIX = "AI-AUDIT-"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"{path}: file not found")
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{number}: invalid JSON") from error
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected a JSON object")
        rows.append(value)
    if not rows:
        raise ValueError(f"{path}: no records")
    return rows


def _read_review_statuses(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"record_id", "review_status", "reviewer_code", "review_note"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path}: missing required review columns")
        rows: dict[str, dict[str, str]] = {}
        for number, row in enumerate(reader, start=2):
            record_id = (row.get("record_id") or "").strip()
            status = (row.get("review_status") or "").strip()
            if not record_id or not status:
                raise ValueError(f"{path}:{number}: record_id and review_status are required")
            if record_id in rows:
                raise ValueError(f"{path}:{number}: duplicate record_id")
            rows[record_id] = {
                "review_status": status,
                "reviewer_code": (row.get("reviewer_code") or "").strip(),
                "review_note": (row.get("review_note") or "").strip(),
            }
    return rows


def export_approved(
    *,
    dataset_path: Path,
    manifest_path: Path,
    review_path: Path,
    output_root: Path,
    minimum_records: int,
) -> dict[str, object]:
    dataset = _read_jsonl(dataset_path)
    manifest = _read_jsonl(manifest_path)
    if len(dataset) != len(manifest):
        raise ValueError("candidate dataset and manifest counts differ")
    review_statuses = _read_review_statuses(review_path)
    approved: list[dict[str, Any]] = []
    approved_manifest: list[dict[str, Any]] = []
    ai_audit_only = 0
    for record, item in zip(dataset, manifest, strict=True):
        record_id = item.get("record_id")
        if not isinstance(record_id, str) or record_id not in review_statuses:
            raise ValueError("every candidate must have a review row")
        review = review_statuses[record_id]
        if review["review_status"] != "approved":
            continue
        if not review["reviewer_code"]:
            raise ValueError(
                f"{record_id}: approved records require a non-identifying reviewer code"
            )
        if review["reviewer_code"].startswith(_AI_AUDIT_PREFIX):
            # An AI audit approval is not a named educator signature and must
            # not be uploaded to MaaS as human-approved training data.
            ai_audit_only += 1
            continue
        approved.append(record)
        approved_manifest.append(
            {
                **item,
                "review_status": "approved",
                "reviewer_code": review["reviewer_code"],
                "review_note": review["review_note"],
            }
        )
    if len(approved) < minimum_records:
        raise ValueError(
            f"only {len(approved)} human-approved records "
            f"({ai_audit_only} AI-audit-only skipped); "
            f"at least {minimum_records} human reviews are required for upload"
        )
    output_root.mkdir(parents=True, exist_ok=True)
    dataset_output = output_root / f"{dataset_path.stem}-approved.jsonl"
    manifest_output = output_root / "approved-manifest.jsonl"
    dataset_output.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in approved) + "\n",
        encoding="utf-8",
    )
    manifest_output.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in approved_manifest) + "\n",
        encoding="utf-8",
    )
    return {
        "records": len(approved),
        "ai_audit_only_skipped": ai_audit_only,
        "dataset": dataset_output.relative_to(REPOSITORY_ROOT).as_posix(),
        "manifest": manifest_output.relative_to(REPOSITORY_ROOT).as_posix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export approved Python tutor SFT records")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_CANDIDATE_ROOT / "sharegpt-python-tutor-v1.jsonl",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_CANDIDATE_ROOT / "review-manifest.jsonl",
    )
    parser.add_argument(
        "--review-queue",
        type=Path,
        default=DEFAULT_CANDIDATE_ROOT / "review-queue.csv",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--minimum-records", type=int, default=200)
    args = parser.parse_args()
    if args.minimum_records < 1:
        raise ValueError("minimum-records must be positive")
    try:
        summary = export_approved(
            dataset_path=args.dataset.resolve(),
            manifest_path=args.manifest.resolve(),
            review_path=args.review_queue.resolve(),
            output_root=args.output_root.resolve(),
            minimum_records=args.minimum_records,
        )
    except (ValueError, OSError) as error:
        print(f"not exported: {error}")
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
