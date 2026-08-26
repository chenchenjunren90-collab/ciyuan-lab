"""Audit teaching quality without changing the frozen course-pack schema.

The structural validator answers whether a record is safe to consume. This
script answers whether the record is substantial enough for human review.
It deliberately reports gaps instead of rewriting or approving course facts.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[1]
COURSE_ROOT = REPO_ROOT / "course_packs"
COURSE_IDS = ("c", "python", "data_structures")
COURSE_LABELS = {
    "c": "C语言程序设计",
    "python": "Python程序设计",
    "data_structures": "数据结构与算法",
}
MIN_SUMMARY_CHARACTERS = 60
MIN_OBJECTIVES = 2
MIN_KEY_POINTS = 3
MIN_EXAMPLES = 1
MIN_COMMON_MISTAKES = 2
REPEATED_ITEM_THRESHOLD = 8


@dataclass(frozen=True)
class ConceptGap:
    concept_id: str
    title: str
    gaps: tuple[str, ...]


@dataclass(frozen=True)
class CourseAudit:
    course_id: str
    title: str
    concepts: int
    exercises: int
    projects: int
    sources: int
    reviewed_sources: int
    rag_eligible_sources: int
    code_or_debug_exercises: int
    code_or_debug_concepts: int
    objective_exercises: int
    short_answer_exercises: int
    draft_records: int
    concepts_ready_for_review: int
    repeated_items: tuple[str, ...]
    concept_gaps: tuple[ConceptGap, ...]


def load_mapping(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source_file:
        document = yaml.safe_load(source_file)
    if not isinstance(document, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} root must be a mapping")
    return document


def load_records(directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        records.append(load_mapping(path))
    return records


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


def visible_characters(value: object) -> int:
    if not isinstance(value, str):
        return 0
    return len(re.sub(r"\s+", "", value))


def repeated_lesson_items(concepts: list[dict[str, Any]]) -> tuple[str, ...]:
    items: Counter[str] = Counter()
    for concept in concepts:
        lesson = concept.get("lesson")
        if not isinstance(lesson, dict):
            continue
        for field in ("key_points", "examples", "common_mistakes"):
            items.update(string_list(lesson.get(field)))
    repeated = [
        f"{text}（重复 {count} 次）"
        for text, count in sorted(items.items(), key=lambda item: (-item[1], item[0]))
        if count >= REPEATED_ITEM_THRESHOLD
    ]
    return tuple(repeated)


def audit_concept(
    concept: dict[str, Any], repeated_texts: set[str], source_status: dict[str, tuple[str, bool]]
) -> ConceptGap:
    gaps: list[str] = []
    lesson_value = concept.get("lesson")
    lesson = cast(dict[str, Any], lesson_value) if isinstance(lesson_value, dict) else {}
    objectives = string_list(concept.get("learning_objectives"))
    key_points = string_list(lesson.get("key_points"))
    examples = string_list(lesson.get("examples"))
    mistakes = string_list(lesson.get("common_mistakes"))
    assessment_ids = string_list(concept.get("assessment_ids"))
    source_refs = string_list(concept.get("source_refs"))

    if len(objectives) < MIN_OBJECTIVES:
        gaps.append(f"学习目标少于 {MIN_OBJECTIVES} 条")
    summary_length = visible_characters(lesson.get("summary"))
    if summary_length < MIN_SUMMARY_CHARACTERS:
        gaps.append(f"讲解摘要仅 {summary_length} 字符，目标不少于 {MIN_SUMMARY_CHARACTERS}")
    if len(key_points) < MIN_KEY_POINTS:
        gaps.append(f"关键点少于 {MIN_KEY_POINTS} 条")
    if len(examples) < MIN_EXAMPLES:
        gaps.append("缺少可阅读或可运行示例")
    if len(mistakes) < MIN_COMMON_MISTAKES:
        gaps.append(f"常见错误少于 {MIN_COMMON_MISTAKES} 条")
    if not assessment_ids:
        gaps.append("未关联练习")
    if not source_refs:
        gaps.append("未关联来源")
    else:
        reviewed_eligible = any(
            source_status.get(source_id) == ("reviewed", True) for source_id in source_refs
        )
        if not reviewed_eligible:
            gaps.append("没有已审核且允许RAG的关联来源")
    repeated = sorted(
        {item for item in (*key_points, *examples, *mistakes) if item in repeated_texts}
    )
    if repeated:
        gaps.append(f"包含模板化重复条目 {len(repeated)} 条")
    if concept.get("status") != "reviewed":
        gaps.append("知识点尚未人工审核")

    return ConceptGap(
        concept_id=str(concept.get("id", "UNKNOWN")),
        title=str(concept.get("title", "未命名")),
        gaps=tuple(gaps),
    )


def audit_course(course_id: str) -> CourseAudit:
    root = COURSE_ROOT / course_id
    concepts = load_records(root / "concepts")
    exercises = load_records(root / "exercises")
    projects = load_records(root / "projects")
    sources = load_records(root / "sources")

    source_status = {
        str(source.get("id")): (
            str(source.get("status", "draft")),
            bool(source.get("rag", {}).get("eligible", False))
            if isinstance(source.get("rag"), dict)
            else False,
        )
        for source in sources
    }
    repeated_rendered = repeated_lesson_items(concepts)
    repeated_texts = {item.rsplit("（重复 ", 1)[0] for item in repeated_rendered}
    gaps = tuple(audit_concept(item, repeated_texts, source_status) for item in concepts)
    practice_exercises = [
        item for item in exercises if item.get("type") in {"code", "debug"}
    ]
    practice_concepts = {
        concept_id
        for item in practice_exercises
        for concept_id in string_list(item.get("concept_ids"))
    }
    all_records = [*concepts, *exercises, *projects, *sources]

    return CourseAudit(
        course_id=course_id,
        title=COURSE_LABELS[course_id],
        concepts=len(concepts),
        exercises=len(exercises),
        projects=len(projects),
        sources=len(sources),
        reviewed_sources=sum(status == "reviewed" for status, _ in source_status.values()),
        rag_eligible_sources=sum(eligible for _, eligible in source_status.values()),
        code_or_debug_exercises=len(practice_exercises),
        code_or_debug_concepts=len(practice_concepts),
        objective_exercises=sum(item.get("type") == "objective" for item in exercises),
        short_answer_exercises=sum(item.get("type") == "short_answer" for item in exercises),
        draft_records=sum(item.get("status") != "reviewed" for item in all_records),
        concepts_ready_for_review=sum(not item.gaps for item in gaps),
        repeated_items=repeated_rendered,
        concept_gaps=gaps,
    )


def render_markdown(audits: list[CourseAudit]) -> str:
    lines = [
        "# 三门课程内容 v2 基线审计",
        "",
        "> 本报告由 `scripts/audit_course_content.py` 根据仓库当前内容生成。",
        "> 自动检查不能替代教师对知识正确性、来源授权和难度的人工审核。",
        "",
        "## 总览",
        "",
        "| 课程 | 知识点 | 练习 | 代码/Debug覆盖知识点 | 项目 | 来源 | "
        "RAG可用来源 | 可送审知识点 | 草稿记录 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for audit in audits:
        lines.append(
            f"| {audit.title} | {audit.concepts} | {audit.exercises} | "
            f"{audit.code_or_debug_concepts} | {audit.projects} | {audit.sources} | "
            f"{audit.rag_eligible_sources} | {audit.concepts_ready_for_review} | "
            f"{audit.draft_records} |"
        )
    lines.extend(
        [
            "",
            "判定说明：只有达到内容 v2 最低质量线、存在已审核可检索来源且知识点本身已审核，",
            "才计入“可送审知识点”。当前为基线阶段，零值不表示结构不可运行，而表示仍需内容审核。",
            "",
        ]
    )

    for audit in audits:
        lines.extend([f"## {audit.title}", ""])
        lines.append(
            f"题型：客观题 {audit.objective_exercises}，代码/Debug题 "
            f"{audit.code_or_debug_exercises}，简答题 {audit.short_answer_exercises}。"
        )
        lines.append("")
        if audit.repeated_items:
            lines.extend(["模板化高频条目：", ""])
            lines.extend(f"- {item}" for item in audit.repeated_items)
            lines.append("")
        lines.extend(
            [
                "| 知识点 | 名称 | 待补或待审内容 |",
                "|---|---|---|",
            ]
        )
        for gap in audit.concept_gaps:
            rendered_gaps = "；".join(gap.gaps) if gap.gaps else "达到自动审计质量线"
            lines.append(f"| {gap.concept_id} | {gap.title} | {rendered_gaps} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--fail-on-gaps",
        action="store_true",
        help="return exit code 1 when any concept has a quality gap",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audits = [audit_course(course_id) for course_id in COURSE_IDS]
    if args.format == "json":
        rendered = (
            json.dumps([asdict(item) for item in audits], ensure_ascii=False, indent=2) + "\n"
        )
    else:
        rendered = render_markdown(audits)

    if args.output:
        output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"Wrote course content audit to {output.relative_to(REPO_ROOT)}")
    else:
        print(rendered, end="")

    has_gaps = any(gap.gaps for audit in audits for gap in audit.concept_gaps)
    return 1 if args.fail_on_gaps and has_gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
