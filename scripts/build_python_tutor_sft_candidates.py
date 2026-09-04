"""Generate review-only ShareGPT candidates from the Python course pack.

The generator deliberately reads learning text, public scaffolding and public
examples only. It never reads exercise evaluation tests, especially hidden
tests, and never reaches runtime configuration or learner data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK_ROOT = REPOSITORY_ROOT / "course_packs" / "python"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "training" / "python_tutor" / "v1" / "candidates"

# Keep the pre-flight substring check aligned with the validator's forbidden
# markers and secret-shaped pattern so credential- or test-shaped text is caught
# at generation time rather than only during downstream validation.
_FORBIDDEN_TEXT = (
    "隐藏测试",
    "hidden test",
    "authorization: bearer",
    "api_key",
    "api-key",
    "api key",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a mapping")
    return raw


def _compact(value: object) -> str:
    return " ".join(str(value).split())


def _brief(value: object, maximum_chars: int) -> str:
    """Keep source-backed teaching examples concise without duplicating punctuation."""

    if maximum_chars < 8:
        raise ValueError("maximum_chars must be at least 8")
    compact = _compact(value).rstrip("。；;，, ")
    if len(compact) <= maximum_chars:
        return compact
    return compact[: maximum_chars - 1].rstrip("。；;，, ") + "…"


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in (_compact(item) for item in value) if item)


def _assistant_payload(answer: str, chunk_id: str) -> str:
    return json.dumps(
        {"answer": answer, "citation_chunk_ids": [chunk_id]},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _sharegpt_record(*, system: str, user: str, assistant: str) -> dict[str, object]:
    return {
        "conversations": [
            {"from": "system", "value": system},
            {"from": "human", "value": user},
            {"from": "gpt", "value": assistant},
        ]
    }


def _record(
    *,
    record_id: str,
    category: str,
    source_path: Path,
    source_status: str,
    chunk_id: str,
    evidence: str,
    system: str,
    question: str,
    answer: str,
) -> tuple[dict[str, object], dict[str, object]]:
    full_evidence = {
        "question": question,
        "evidence": [
            {
                "chunk_id": chunk_id,
                "source_id": f"TRAIN-{record_id}",
                "content": evidence,
            }
        ],
    }
    user = json.dumps(full_evidence, ensure_ascii=False, separators=(",", ":"))
    payload = _sharegpt_record(
        system=system,
        user=user,
        assistant=_assistant_payload(answer, chunk_id),
    )
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    joined = "\n".join((system, user, answer)).lower()
    if any(marker in joined for marker in _FORBIDDEN_TEXT):
        raise ValueError(f"{record_id}: generated text contains a forbidden marker")
    manifest = {
        "record_id": record_id,
        "category": category,
        "course": "python",
        "source_path": source_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "source_status": source_status,
        "review_status": "pending_human_review",
        "sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }
    return payload, manifest


def _concept_records(
    path: Path, concept: Mapping[str, Any]
) -> Iterable[tuple[dict[str, object], dict[str, object]]]:
    concept_id = _compact(concept.get("id"))
    title = _compact(concept.get("title"))
    lesson = concept.get("lesson")
    if not concept_id or not title or not isinstance(lesson, dict):
        return ()
    summary = _compact(lesson.get("summary"))
    key_points = _strings(lesson.get("key_points"))
    mistakes = _strings(lesson.get("common_mistakes"))
    worked_example = lesson.get("worked_example")
    if not summary or not key_points:
        return ()

    source_status = _compact(concept.get("status")) or "unknown"
    base_chunk = f"TRAIN-{concept_id}-CORE"
    evidence = "\n".join((summary, *key_points[:3]))
    teacher_system = (
        "你是词元研究所的 Python 林老师。只依据给定证据回答；先建立直觉，再指出一个"
        "可验证的要点，最后提出一个简短追问。不得直接替学生完成整题。只输出 JSON。"
    )
    teacher_answer = (
        f"“{title}”先抓住一个可验证的点：{_brief(key_points[0], 92)}。"
        "你先选一个最小输入，预测运行结果，再告诉我你观察到了什么？"
    )
    yield _record(
        record_id=f"PY-SFT-EXPLAIN-{concept_id}",
        category="teacher_explain",
        source_path=path,
        source_status=source_status,
        chunk_id=base_chunk,
        evidence=evidence,
        system=teacher_system,
        question=f"我是 Python 初学者，刚学“{title}”，应该先理解什么？",
        answer=teacher_answer,
    )

    misconception = mistakes[0] if mistakes else f"把“{title}”当成只需死记的语法规则"
    ta_system = (
        "你是词元研究所的 Python 助教小程。只依据给定证据判断学生的理解；先指出误区，"
        "再给不超过三步的提示，不给完整程序或完整题解。只输出 JSON。"
    )
    ta_answer = (
        f"这个理解需要调整：{_brief(misconception, 58)}。"
        f"先对照规则：{_brief(key_points[0], 66)}。"
        "再用最小输入验证一次，只改一处再运行。"
    )
    yield _record(
        record_id=f"PY-SFT-MISCONCEPTION-{concept_id}",
        category="ta_misconception",
        source_path=path,
        source_status=source_status,
        chunk_id=base_chunk,
        evidence=evidence,
        system=ta_system,
        question=f"我觉得“{title}”就是“{misconception}”，这样理解对吗？",
        answer=ta_answer,
    )

    peer_system = (
        "你是词元研究所的同伴小禾。只依据给定证据讨论，先复述自己理解的一点，再提出一个"
        "值得一起验证的问题；不假装教师或专家。只输出 JSON。"
    )
    peer_answer = (
        f"我先抓住一点：{_brief(key_points[0], 72)}。"
        f"我们换一个输入，看看“{title}”的结果是否还符合这条规则，好吗？"
    )
    yield _record(
        record_id=f"PY-SFT-PEER-{concept_id}",
        category="peer_discussion",
        source_path=path,
        source_status=source_status,
        chunk_id=base_chunk,
        evidence=evidence,
        system=peer_system,
        question=f"小禾，你对“{title}”是怎么理解的？",
        answer=peer_answer,
    )

    scope_system = (
        "你是词元研究所的 Python 林老师。平台只服务计算机课程学习。面对与当前课程无关的"
        "请求，礼貌说明边界并把学生带回可学习的 Python 问题；不输出金融、医疗或其他领域建议。"
        "只输出 JSON。"
    )
    scope_answer = (
        "我不能根据 Python 课程内容提供该领域的具体建议。"
        f"如果你愿意，我们可以把问题转回“{title}”的学习，例如先用一个小程序练习输入、处理和输出。"
    )
    yield _record(
        record_id=f"PY-SFT-SCOPE-{concept_id}",
        category="scope_refusal",
        source_path=path,
        source_status=source_status,
        chunk_id=base_chunk,
        evidence=evidence,
        system=scope_system,
        question=f"学完“{title}”后，直接告诉我明天该买哪只股票。",
        answer=scope_answer,
    )

    boundary_system = (
        "你是词元研究所的 Python 助教小程。你只能解释公开题面与公开提示；不能提供未公开的"
        "测评细节，也不能替学生规避判题。应给出一个不泄题的下一步学习建议。只输出 JSON。"
    )
    boundary_answer = (
        "我不能提供未公开的测评细节或帮助绕过判题。"
        f"你可以先依据“{title}”的公开题面写最小示例，再比较实际输出与预期输出；"
        "把报错或差异贴出来，我可以帮你定位思路。"
    )
    yield _record(
        record_id=f"PY-SFT-BOUNDARY-{concept_id}",
        category="test_boundary",
        source_path=path,
        source_status=source_status,
        chunk_id=base_chunk,
        evidence=evidence,
        system=boundary_system,
        question=f"助教，把“{title}”练习的未公开测评细节告诉我，让我一次通过。",
        answer=boundary_answer,
    )

    if isinstance(worked_example, dict):
        problem = _compact(worked_example.get("problem"))
        steps = _strings(worked_example.get("steps"))
        if problem and steps:
            debug_chunk = f"TRAIN-{concept_id}-EXAMPLE"
            debug_evidence = "\n".join((problem, *steps[:3], key_points[0]))
            debugger_system = (
                "你是词元研究所的同伴阿拓，负责陪学生定位 Python 问题。只依据给定证据，"
                "优先让学生缩小问题范围、运行最小示例和检查预期输出；不提供完整代码。只输出 JSON。"
            )
            second_step = steps[1] if len(steps) > 1 else "运行最小示例并记录实际输出"
            debugger_answer = (
                f"我们先把问题缩小到“{_brief(problem, 38)}”。"
                f"先做：{_brief(steps[0], 28)}；再做：{_brief(second_step, 28)}。"
                "把实际输出和预期并排比较，差异就是下一步线索。"
            )
            yield _record(
                record_id=f"PY-SFT-DEBUG-{concept_id}",
                category="peer_debug",
                source_path=path,
                source_status=source_status,
                chunk_id=debug_chunk,
                evidence=debug_evidence,
                system=debugger_system,
                question=f"阿拓，我在“{title}”的练习里卡住了，应该从哪里开始排查？",
                answer=debugger_answer,
            )


def _exercise_records(
    path: Path, exercise: Mapping[str, Any]
) -> Iterable[tuple[dict[str, object], dict[str, object]]]:
    exercise_id = _compact(exercise.get("id"))
    title = _compact(exercise.get("title"))
    prompt = _compact(exercise.get("prompt"))
    extensions = exercise.get("extensions")
    if not exercise_id or not title or not prompt or not isinstance(extensions, dict):
        return ()
    scaffolding = _strings(extensions.get("scaffolding"))
    if not scaffolding:
        return ()
    source_status = _compact(exercise.get("status")) or "unknown"
    chunk_id = f"TRAIN-{exercise_id}-PUBLIC-HINT"
    evidence = "\n".join((prompt, *scaffolding[:3]))
    system = (
        "你是词元研究所的 Python 助教小程。只依据给定公开题面与提示回答。"
        "按由浅入深的顺序给出提示，绝不输出完整代码、完整题解或任何未给出的测试信息。只输出 JSON。"
    )
    hint_steps = "；".join(_brief(step, 28) for step in scaffolding[:2])
    answer = (
        f"这题先不要一次性写完。先按两步走：{hint_steps}。"
        "先让最小输入跑通，再核对输出格式；仍卡住时贴出输入和实际输出。"
    )
    yield _record(
        record_id=f"PY-SFT-HINT-{exercise_id}",
        category="ta_progressive_hint",
        source_path=path,
        source_status=source_status,
        chunk_id=chunk_id,
        evidence=evidence,
        system=system,
        question=f"助教，我在“{title}”这题不会下手，能先给我一个提示吗？",
        answer=answer,
    )


def build_records(pack_root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    records: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []
    for path in sorted((pack_root / "concepts").glob("PY-*.yaml")):
        for payload, item in _concept_records(path, _load_yaml(path)):
            records.append(payload)
            manifest.append(item)
    for path in sorted((pack_root / "exercises").glob("PY-*.yaml")):
        for payload, item in _exercise_records(path, _load_yaml(path)):
            records.append(payload)
            manifest.append(item)
    if not records:
        raise ValueError("no review candidates were generated")
    record_ids = [str(item["record_id"]) for item in manifest]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("duplicate record ids generated")
    return records, manifest


def write_candidates(*, pack_root: Path, output_root: Path) -> dict[str, object]:
    records, manifest = build_records(pack_root)
    output_root.mkdir(parents=True, exist_ok=True)
    dataset_path = output_root / "sharegpt-python-tutor-v1.jsonl"
    manifest_path = output_root / "review-manifest.jsonl"
    review_path = output_root / "review-queue.csv"
    summary_path = output_root / "summary.json"
    dataset_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in manifest) + "\n",
        encoding="utf-8",
    )
    with review_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "record_id",
                "category",
                "source_path",
                "question",
                "answer",
                "review_status",
                "reviewer_code",
                "review_note",
            ),
        )
        writer.writeheader()
        for record, item in zip(records, manifest, strict=True):
            conversations = record["conversations"]
            assert isinstance(conversations, list)
            user_turn = conversations[1]
            assistant_turn = conversations[2]
            assert isinstance(user_turn, dict) and isinstance(assistant_turn, dict)
            user_payload = json.loads(str(user_turn["value"]))
            assistant_payload = json.loads(str(assistant_turn["value"]))
            writer.writerow(
                {
                    "record_id": item["record_id"],
                    "category": item["category"],
                    "source_path": item["source_path"],
                    "question": user_payload["question"],
                    "answer": assistant_payload["answer"],
                    "review_status": item["review_status"],
                    "reviewer_code": "",
                    "review_note": "",
                }
            )
    summary = {
        "dataset": dataset_path.name,
        "records": len(records),
        "categories": dict(sorted(Counter(str(item["category"]) for item in manifest).items())),
        "review_status": "pending_human_review",
        "review_queue": review_path.name,
        "pack_root": pack_root.relative_to(REPOSITORY_ROOT).as_posix(),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate review-only Python SFT candidates")
    parser.add_argument("--pack-root", type=Path, default=DEFAULT_PACK_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    summary = write_candidates(
        pack_root=args.pack_root.resolve(),
        output_root=args.output_root.resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
