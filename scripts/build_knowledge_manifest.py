"""Build a reviewable knowledge-ingestion manifest without writing a database."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.modules.course_content import CoursePackRepository
from app.modules.rag.ingestion import build_ingestion_plan

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/audits/knowledge-ingestion-manifest.json"),
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    plan = build_ingestion_plan(CoursePackRepository())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(plan.to_json(), encoding="utf-8")
    print(
        f"Wrote {len(plan.candidates)} candidates: {plan.eligible_count} eligible, "
        f"{plan.blocked_count} blocked -> {output.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
