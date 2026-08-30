from scripts.audit_course_content import COURSE_IDS, audit_course, render_markdown


def test_audit_covers_all_three_mvp_courses() -> None:
    audits = [audit_course(course_id) for course_id in COURSE_IDS]

    assert [audit.course_id for audit in audits] == ["c", "python", "data_structures"]
    assert {audit.course_id: audit.concepts for audit in audits} == {
        "c": 42,
        "python": 40,
        "data_structures": 40,
    }
    assert {audit.course_id: audit.exercises for audit in audits} == {
        "c": 42,
        "python": 80,
        "data_structures": 40,
    }
    assert all(audit.projects >= 1 for audit in audits)
    assert all(len(audit.concept_gaps) == audit.concepts for audit in audits)


def test_audit_confirms_template_repetition_was_removed() -> None:
    c_audit = audit_course("c")

    assert c_audit.repeated_items == ()
    pointer_gap = next(gap for gap in c_audit.concept_gaps if gap.concept_id == "C-PTR-01")
    assert pointer_gap.gaps == ("知识点尚未人工审核",)


def test_markdown_report_contains_metrics_and_per_concept_findings() -> None:
    report = render_markdown([audit_course(course_id) for course_id in COURSE_IDS])

    assert "# 三门课程内容 v2 基线审计" in report
    assert "| C语言程序设计 | 42 | 42 |" in report
    assert "| PY-FUNC-01 | 函数定义与调用 |" in report
    assert "| DS-TREE-01 | 树、结点关系与基本术语 |" in report


def test_enriched_cards_only_wait_for_human_review() -> None:
    audits = [audit_course(course_id) for course_id in COURSE_IDS]

    assert all(
        gap.gaps == ("知识点尚未人工审核",) for audit in audits for gap in audit.concept_gaps
    )
