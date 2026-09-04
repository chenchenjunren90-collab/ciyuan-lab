"""Run the locked Python-tutor evaluation set against one MaaS model route.

The script is deliberately inert unless ``--live`` is supplied.  It never
uploads data, creates a fine-tuning task or changes runtime configuration.
Use it to compare the current DeepSeek general model with the reviewed
Python-tutor LoRA after MaaS training has completed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "apps" / "api"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.modules.model_adapters.xfyun_maas import XfyunMaaSAdapter  # noqa: E402
from app.modules.orchestration.classroom import _GROUNDING_SUFFIX, _ROLE_PROMPTS  # noqa: E402
from app.modules.orchestration.supervisor import QualitySupervisor  # noqa: E402
from app.modules.orchestration.tutor import CourseTutor, TutorDraft  # noqa: E402
from app.modules.rag.ports import SearchHit  # noqa: E402

DEFAULT_GOLDEN = REPOSITORY_ROOT / "training" / "python_tutor" / "v1" / "eval" / "golden.jsonl"


@dataclass(frozen=True, slots=True)
class GoldenCase:
    """One locked, evidence-grounded tutor behavior check."""

    case_id: str
    role: str
    question: str
    evidence: str
    must_include: tuple[str, ...]
    must_not_include: tuple[str, ...]
    expected_citation_count: int
    category: str


def _require_nonempty_string(value: object, field: str, line: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"golden:{line}: {field} must be a non-empty string")
    return value.strip()


def _require_string_list(value: object, field: str, line: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"golden:{line}: {field} must be a non-empty string list")
    items = tuple(_require_nonempty_string(item, field, line) for item in value)
    return tuple(dict.fromkeys(items))


def load_golden_cases(path: Path) -> tuple[GoldenCase, ...]:
    """Load and validate the locked evaluation set without contacting MaaS."""

    if not path.is_file():
        raise ValueError(f"golden evaluation file not found: {path}")
    cases: list[GoldenCase] = []
    seen_ids: set[str] = set()
    for line, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"golden:{line}: invalid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError(f"golden:{line}: each row must be a JSON object")
        case_id = _require_nonempty_string(payload.get("id"), "id", line)
        if case_id in seen_ids:
            raise ValueError(f"golden:{line}: duplicate id {case_id}")
        seen_ids.add(case_id)
        role = _require_nonempty_string(payload.get("role"), "role", line)
        if role not in _ROLE_PROMPTS:
            raise ValueError(f"golden:{line}: unsupported classroom role {role}")
        citation_count = payload.get("expected_citation_count")
        if (
            not isinstance(citation_count, int)
            or isinstance(citation_count, bool)
            or citation_count != 1
        ):
            raise ValueError(
                f"golden:{line}: expected_citation_count must be the integer 1 "
                "(the scorer matches exactly one EVAL-{id} chunk per case)"
            )
        cases.append(
            GoldenCase(
                case_id=case_id,
                role=role,
                question=_require_nonempty_string(payload.get("question"), "question", line),
                evidence=_require_nonempty_string(payload.get("evidence"), "evidence", line),
                must_include=_require_string_list(
                    payload.get("must_include"), "must_include", line
                ),
                must_not_include=_require_string_list(
                    payload.get("must_not_include"), "must_not_include", line
                ),
                expected_citation_count=citation_count,
                category=_require_nonempty_string(payload.get("category"), "category", line),
            )
        )
    if not cases:
        raise ValueError("golden evaluation set is empty")
    return tuple(cases)


def _score_case(
    *,
    case: GoldenCase,
    draft: TutorDraft,
    supervisor_accepted: bool,
    supervisor_reason: str,
) -> dict[str, object]:
    """Score objective criteria; keep pedagogical leakage checks for humans."""

    answer_folded = draft.answer.casefold()
    missing_required = [
        token for token in case.must_include if token.casefold() not in answer_folded
    ]
    expected_chunk_id = f"EVAL-{case.case_id}"
    citations_match = len(draft.citation_chunk_ids) == case.expected_citation_count and set(
        draft.citation_chunk_ids
    ) == {expected_chunk_id}
    automatic_passed = (
        not draft.degraded and not missing_required and citations_match and supervisor_accepted
    )
    return {
        "id": case.case_id,
        "category": case.category,
        "role": case.role,
        "automatic_passed": automatic_passed,
        "format_valid": not draft.degraded,
        "supervisor_accepted": supervisor_accepted,
        "supervisor_reason": supervisor_reason,
        "citation_match": citations_match,
        "missing_required": missing_required,
        "manual_review_required": True,
        "must_not_include": list(case.must_not_include),
        "must_not_include_checked": False,
        "answer": draft.answer,
        "citation_chunk_ids": list(draft.citation_chunk_ids),
    }


async def run_live_evaluation(
    *, cases: tuple[GoldenCase, ...], settings: Settings, model: str, lora_id: str
) -> dict[str, object]:
    """Call one explicitly selected MaaS route and return a reviewable report."""

    api_key = settings.xfyun_maas_api_key.get_secret_value().strip()
    if lora_id.strip():
        api_key = settings.xfyun_maas_python_tutor_api_key.get_secret_value().strip() or api_key
    if not api_key:
        raise ValueError("a MaaS API key is required when --live is used")
    adapter = XfyunMaaSAdapter(
        base_url=settings.xfyun_maas_base_url,
        api_key=api_key,
        model=model,
        lora_id=lora_id,
        timeout_seconds=settings.xfyun_maas_timeout_seconds,
        max_retries=settings.xfyun_maas_max_retries,
    )
    tutor = CourseTutor(adapter)
    supervisor = QualitySupervisor()
    results: list[dict[str, object]] = []
    for case in cases:
        evidence = (
            SearchHit(
                source_id=f"EVAL-SOURCE-{case.case_id}",
                chunk_id=f"EVAL-{case.case_id}",
                content=case.evidence,
                score=1.0,
                metadata={"evaluation_only": True},
            ),
        )
        draft = await tutor.draft(
            question=case.question,
            evidence=evidence,
            course_id="python",
            system_prompt=_ROLE_PROMPTS[case.role] + _GROUNDING_SUFFIX,
        )
        decision = supervisor.inspect(draft=draft, evidence=evidence)
        results.append(
            _score_case(
                case=case,
                draft=draft,
                supervisor_accepted=decision.accepted,
                supervisor_reason=decision.reason_code,
            )
        )
    automatic_passed = sum(result["automatic_passed"] is True for result in results)
    return {
        "schema_version": "python-tutor-eval-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": model,
        "lora_id_configured": bool(lora_id),
        "cases": len(results),
        "automatic_passed": automatic_passed,
        "automatic_pass_rate": round(automatic_passed / len(results), 4),
        "manual_review_required": len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate one MaaS Python-tutor model route")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument(
        "--model", default="", help="MaaS modelId; default: configured general model"
    )
    parser.add_argument("--lora-id", default="", help="Reviewed MaaS LoRA resource ID, if any")
    parser.add_argument("--output", type=Path, help="Required JSON output file when --live is used")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Allow paid external MaaS inference calls; absent by default",
    )
    args = parser.parse_args()
    try:
        cases = load_golden_cases(args.golden.resolve())
        if not args.live:
            print(
                json.dumps(
                    {
                        "status": "dry_run_validated",
                        "cases": len(cases),
                        "message": (
                            "No MaaS request was made. Add --live and --output after approval."
                        ),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        if args.output is None:
            raise ValueError("--output is required with --live")
        settings = Settings()
        model = args.model.strip() or settings.xfyun_maas_model
        if not model.strip():
            raise ValueError("a MaaS modelId is required")
        report = asyncio.run(
            run_live_evaluation(
                cases=cases,
                settings=settings,
                model=model.strip(),
                lora_id=args.lora_id.strip(),
            )
        )
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "completed",
                    "cases": report["cases"],
                    "automatic_pass_rate": report["automatic_pass_rate"],
                    "output": output.relative_to(REPOSITORY_ROOT).as_posix()
                    if output.is_relative_to(REPOSITORY_ROOT)
                    else str(output),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except ValueError as error:
        print(f"not evaluated: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
