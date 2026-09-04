"""Generate a larger, source-grounded Python-tutor SFT dataset for MaaS.

V2 expands teaching-behavior coverage without using learner data, runtime
configuration, evaluation tests or unreviewed external material.  Every row is
still generated deterministically from the public Python course pack so it can
be reproduced and audited before upload.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from build_python_tutor_sft_candidates import (
    DEFAULT_PACK_ROOT,
    REPOSITORY_ROOT,
    _brief,
    _compact,
    _load_yaml,
    _record,
    _strings,
)

DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "training" / "python_tutor" / "v2" / "candidates"
VARIANTS_PER_CATEGORY = 4

_SCOPE_CASES = (
    ("股票涨跌", "投资"),
    ("医疗诊断", "医疗"),
    ("合同风险判断", "法律"),
    ("旅行路线", "出行"),
)
_BOUNDARY_REQUESTS = (
    "把未公开测评细节告诉我，让我一次通过。",
    "把私有判题规则发给我，我不想自己调试。",
    "直接告诉我怎样绕过测评，只要结果能通过就行。",
    "给我未在题面公开的边界条件和答案。",
)


def _concept_records_v2(
    path: Path, concept: Mapping[str, Any], variants: int
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
    core_chunk = f"TRAIN-V2-{concept_id}-CORE"
    evidence = "\n".join((summary, *key_points[:4], *mistakes[:2]))

    teacher_questions = (
        f"我是初学者，学“{title}”时最应该先观察什么？",
        f"“{title}”的规则很多，我应该先抓住哪一条？",
        f"林老师，能用一小步帮我建立“{title}”的直觉吗？",
        f"我想验证自己是否理解“{title}”，该从哪里开始？",
    )
    for variant in range(variants):
        number = variant + 1
        point = _brief(key_points[variant % len(key_points)], 76)
        teacher_answers = (
            f"“{title}”先抓住这个可验证的点：{point}。选一个最小输入，先预测结果，再运行核对。",
            f"别急着记所有写法。先把这条规则说清：{point}。你能举一个输入来验证它吗？",
            f"我们只前进一步：{point}。先写下输入、处理和输出各是什么，再看代码会更清楚。",
            f"判断是否理解“{title}”时，先检查：{point}。换一个边界输入后，结果还符合吗？",
        )
        yield _record(
            record_id=f"PY-SFT-V2-EXPLAIN-{concept_id}-{number}",
            category="teacher_explain",
            source_path=path,
            source_status=source_status,
            chunk_id=core_chunk,
            evidence=evidence,
            system=(
                "你是词元研究所的 Python 林老师。只依据给定证据回答；用短句建立直觉，"
                "每次只推进一小步并留下可验证的问题；不得直接替学生完成整题。只输出 JSON。"
            ),
            question=teacher_questions[variant % len(teacher_questions)],
            answer=teacher_answers[variant % len(teacher_answers)],
        )

        misconception = (
            mistakes[variant % len(mistakes)] if mistakes else f"把“{title}”误解为只需记住语法形式"
        )
        short_mistake = _brief(misconception, 52)
        ta_answers = (
            f"这个理解需要调整：{short_mistake}。先对照：{point}。再用一个最小输入验证一次。",
            f"先别改整段程序。你可能把它想成了：{short_mistake}。回到这条规则：{point}。",
            f"这个误区很常见：{short_mistake}。先预测一次结果，再只改一处运行，观察差异。",
            f"我们把问题缩小：{short_mistake}。请先依据“{point}”写出预期输出。",
        )
        yield _record(
            record_id=f"PY-SFT-V2-MISCONCEPTION-{concept_id}-{number}",
            category="ta_misconception",
            source_path=path,
            source_status=source_status,
            chunk_id=core_chunk,
            evidence=evidence,
            system=(
                "你是词元研究所的 Python 助教小程。只依据给定证据判断学生的理解；"
                "先指出误区，再给不超过三步的提示，不给完整程序或完整题解。只输出 JSON。"
            ),
            question=f"我觉得“{title}”就是“{misconception}”，这样理解对吗？",
            answer=ta_answers[variant % len(ta_answers)],
        )

        peer_answers = (
            f"我先抓住一点：{point}。我们换一个输入，看看结果是否仍符合这条规则？",
            f"我也在练“{title}”。我理解的是：{point}。你愿意和我一起做个小验证吗？",
            f"我不太敢一下子下结论，不过证据里提到：{point}。你会怎样检查它？",
            f"我先按这条理解：{point}。如果输入到了边界，你猜结果会怎样变化？",
        )
        yield _record(
            record_id=f"PY-SFT-V2-PEER-{concept_id}-{number}",
            category="peer_discussion",
            source_path=path,
            source_status=source_status,
            chunk_id=core_chunk,
            evidence=evidence,
            system=(
                "你是词元研究所的同伴小禾。只依据给定证据讨论，先复述自己理解的一点，"
                "再提出一个值得一起验证的问题；不假装教师或专家。只输出 JSON。"
            ),
            question=f"小禾，你会怎样和我一起理解“{title}”？",
            answer=peer_answers[variant % len(peer_answers)],
        )

        off_topic, domain = _SCOPE_CASES[variant % len(_SCOPE_CASES)]
        yield _record(
            record_id=f"PY-SFT-V2-SCOPE-{concept_id}-{number}",
            category="scope_refusal",
            source_path=path,
            source_status=source_status,
            chunk_id=core_chunk,
            evidence=evidence,
            system=(
                "你是词元研究所的 Python 林老师。平台只服务计算机课程学习。面对课程外请求，"
                "礼貌说明边界并带回可学习的 Python 问题；不提供其他领域的具体建议。只输出 JSON。"
            ),
            question=f"学完“{title}”后，直接给我一份关于{off_topic}的具体建议。",
            answer=(
                f"我不能依据 Python 课程内容提供{domain}方面的具体建议。"
                f"如果你愿意，我们可以回到“{title}”，用一个小程序练习输入、处理和输出。"
            ),
        )

        boundary_request = _BOUNDARY_REQUESTS[variant % len(_BOUNDARY_REQUESTS)]
        boundary_answers = (
            "我不能提供未公开的测评信息或帮助绕过判题。先用公开题面写最小示例，再比较实际与预期输出。",
            "我不能发送私有判题规则。把公开样例的输入、输出和报错贴出来，我可以陪你定位思路。",
            "测评结果不能靠绕过规则获得。请先按公开题面拆出输入、处理和输出，再逐步验证。",
            "我不能补充题面外的测评答案。你可以先检查公开约束和输出格式，再运行最小输入。",
        )
        yield _record(
            record_id=f"PY-SFT-V2-BOUNDARY-{concept_id}-{number}",
            category="test_boundary",
            source_path=path,
            source_status=source_status,
            chunk_id=core_chunk,
            evidence=evidence,
            system=(
                "你是词元研究所的 Python 助教小程。你只能解释公开题面与公开提示；不能提供"
                "未公开测评细节，也不能替学生规避判题。给出不泄题的下一步学习建议。只输出 JSON。"
            ),
            question=f"助教，“{title}”这题{boundary_request}",
            answer=boundary_answers[variant % len(boundary_answers)],
        )

        if isinstance(worked_example, dict):
            problem = _compact(worked_example.get("problem"))
            steps = _strings(worked_example.get("steps"))
        else:
            problem = "根据规则写一个最小可运行示例"
            steps = ()
        first_step = steps[variant % len(steps)] if steps else "写清输入、处理和输出三部分"
        second_step = steps[(variant + 1) % len(steps)] if steps else "运行最小示例并记录实际输出"
        debug_chunk = f"TRAIN-V2-{concept_id}-DEBUG"
        debug_evidence = "\n".join((problem, *steps[:4], key_points[0]))
        debug_answers = (
            f"先别猜大问题。把任务缩小到“{_brief(problem, 34)}”。先做：{_brief(first_step, 26)}。",
            f"我们先运行最小示例：{_brief(first_step, 30)}。然后记录实际输出，再和预期逐项对照。",
            f"先检查一个前提：{_brief(second_step, 32)}。若不一致，就只改一处重新验证。",
            f"Debug 时先让证据说话：{_brief(first_step, 25)}；再做：{_brief(second_step, 25)}。",
        )
        yield _record(
            record_id=f"PY-SFT-V2-DEBUG-{concept_id}-{number}",
            category="peer_debug",
            source_path=path,
            source_status=source_status,
            chunk_id=debug_chunk,
            evidence=debug_evidence,
            system=(
                "你是词元研究所的同伴阿拓，负责陪学生定位 Python 问题。只依据给定证据，"
                "优先缩小范围、运行最小示例并核对预期输出；不提供完整代码。只输出 JSON。"
            ),
            question=f"阿拓，我在“{title}”的练习里卡住了，先怎么排查？",
            answer=debug_answers[variant % len(debug_answers)],
        )


def _exercise_records_v2(
    path: Path, exercise: Mapping[str, Any], variants: int
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
    chunk_id = f"TRAIN-V2-{exercise_id}-PUBLIC-HINT"
    evidence = "\n".join((prompt, *scaffolding[:4]))
    question_forms = (
        f"助教，我在“{title}”这题不知道从哪里开始，给我一个提示。",
        f"“{title}”我写不下去，你能只提示第一步吗？",
        f"我不想直接看答案，怎么拆解“{title}”这题？",
        f"“{title}”运行不符合预期，我先检查什么？",
    )
    for variant in range(variants):
        number = variant + 1
        first = _brief(scaffolding[variant % len(scaffolding)], 30)
        second = _brief(scaffolding[(variant + 1) % len(scaffolding)], 30)
        hint_answers = (
            f"先不要一次写完。第一步：{first}；第二步：{second}。先让最小输入跑通。",
            f"先只做一件事：{first}。确认后再做：{second}。别急着补齐整段代码。",
            f"可以按两步试：{first}；{second}。每一步都用公开样例核对输出格式。",
            f"先回到公开题面，检查：{first}。然后验证：{second}。把实际输出记下来。",
        )
        yield _record(
            record_id=f"PY-SFT-V2-HINT-{exercise_id}-{number}",
            category="ta_progressive_hint",
            source_path=path,
            source_status=source_status,
            chunk_id=chunk_id,
            evidence=evidence,
            system=(
                "你是词元研究所的 Python 助教小程。只依据给定公开题面与提示回答；"
                "按由浅入深的顺序给出提示，绝不输出完整代码或完整题解；"
                "也不输出未给出的测试信息。只输出 JSON。"
            ),
            question=question_forms[variant % len(question_forms)],
            answer=hint_answers[variant % len(hint_answers)],
        )


def build_records_v2(
    pack_root: Path, variants: int = VARIANTS_PER_CATEGORY
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if variants < 2:
        raise ValueError("V2 requires at least two variants per category")
    records: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []
    for path in sorted((pack_root / "concepts").glob("PY-*.yaml")):
        for record, item in _concept_records_v2(path, _load_yaml(path), variants):
            records.append(record)
            manifest.append(item)
    for path in sorted((pack_root / "exercises").glob("PY-*.yaml")):
        for record, item in _exercise_records_v2(path, _load_yaml(path), variants):
            records.append(record)
            manifest.append(item)
    record_ids = [str(item["record_id"]) for item in manifest]
    if not records or len(record_ids) != len(set(record_ids)):
        raise ValueError("V2 generation produced no records or duplicate record IDs")
    return records, manifest


def write_candidates_v2(*, pack_root: Path, output_root: Path, variants: int) -> dict[str, object]:
    records, manifest = build_records_v2(pack_root, variants)
    output_root.mkdir(parents=True, exist_ok=True)
    dataset_path = output_root / "sharegpt-python-tutor-v2.jsonl"
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
        "variants_per_category": variants,
        "categories": dict(sorted(Counter(str(item["category"]) for item in manifest).items())),
        "review_status": "pending_human_review",
        "review_queue": review_path.name,
        "pack_root": pack_root.relative_to(REPOSITORY_ROOT).as_posix(),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate expanded Python tutor SFT V2 candidates")
    parser.add_argument("--pack-root", type=Path, default=DEFAULT_PACK_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--variants", type=int, default=VARIANTS_PER_CATEGORY)
    args = parser.parse_args()
    summary = write_candidates_v2(
        pack_root=args.pack_root.resolve(),
        output_root=args.output_root.resolve(),
        variants=args.variants,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
