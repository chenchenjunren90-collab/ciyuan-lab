from scripts.audit_course_content import COURSE_IDS, audit_course, render_markdown


def test_audit_covers_all_three_mvp_courses() -> None:
    audits = [audit_course(course_id) for course_id in COURSE_IDS]

    assert [audit.course_id for audit in audits] == ["c", "python", "data_structures"]
    assert all(audit.concepts == 40 for audit in audits)
    assert all(audit.exercises == 40 for audit in audits)
    assert all(audit.projects >= 1 for audit in audits)
    assert all(len(audit.concept_gaps) == audit.concepts for audit in audits)


def test_audit_exposes_template_repetition_and_review_gaps() -> None:
    c_audit = audit_course("c")

    assert any("重复 40 次" in item for item in c_audit.repeated_items)
    pointer_gap = next(
        gap for gap in c_audit.concept_gaps if gap.concept_id == "C-PTR-01"
    )
    assert "缺少可阅读或可运行示例" in pointer_gap.gaps
    assert "知识点尚未人工审核" in pointer_gap.gaps


def test_markdown_report_contains_metrics_and_per_concept_findings() -> None:
    report = render_markdown([audit_course(course_id) for course_id in COURSE_IDS])

    assert "# 三门课程内容 v2 基线审计" in report
    assert "| C语言程序设计 | 40 | 40 |" in report
    assert "| PY-FUNC-01 | 函数定义与调用 |" in report
    assert "| DS-TREE-01 | 树、结点关系与基本术语 |" in report

