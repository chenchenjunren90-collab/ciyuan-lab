"""Role-aware classroom context must stay useful and bounded."""

from dataclasses import dataclass

from app.modules.orchestration.dialogue_context import build_dialogue_context


@dataclass(frozen=True)
class Turn:
    role: str
    content: str


ROLE_NAMES = {
    "teacher": "林老师",
    "ta": "助教小程",
    "peer_debugger": "阿拓",
}


def test_context_preserves_active_agent_and_peer_identity() -> None:
    context = build_dialogue_context(
        message="再讲一下",
        recent_turns=(
            Turn("student", "print 是什么意思？"),
            Turn("teacher", "print 会把内容显示到标准输出。"),
            Turn("peer_debugger", "我会运行一个最小例子验证。"),
        ),
        current_role="teacher",
        role_names=ROLE_NAMES,
        lesson_topic="Python 解释器与输出",
        contextual=True,
    )

    assert [item.role for item in context.model_messages] == ["user", "assistant", "user"]
    assert context.model_messages[0].content == "print 是什么意思？"
    assert context.model_messages[1].content.startswith("print 会")
    assert context.model_messages[2].content.startswith("[阿拓（课堂同伴）]:")
    assert "避免复述其他角色" in context.instruction


def test_contextual_retrieval_uses_student_topic_instead_of_agent_chatter() -> None:
    context = build_dialogue_context(
        message="那它到底做什么？",
        recent_turns=(
            Turn("student", "print 是什么意思？"),
            Turn("teacher", "先看课程知识点。"),
            Turn("peer_debugger", "列表循环和字典都是别的话题。"),
            Turn("student", "好的"),
        ),
        current_role="teacher",
        role_names=ROLE_NAMES,
        lesson_topic="Python 列表与循环",
        contextual=True,
    )

    assert "print 是什么意思" in context.retrieval_query
    assert "那它到底做什么" in context.retrieval_query
    assert "列表循环和字典" not in context.retrieval_query
    assert "Python 列表与循环" not in context.retrieval_query


def test_empty_or_failed_history_is_removed_from_model_context() -> None:
    context = build_dialogue_context(
        message="请继续",
        recent_turns=(
            Turn("teacher", "..."),
            Turn("student", "  ……  "),
            Turn("student", "解释器怎样运行程序？"),
        ),
        current_role="teacher",
        role_names=ROLE_NAMES,
        lesson_topic="Python 解释器",
        contextual=True,
    )

    assert len(context.model_messages) == 1
    assert context.model_messages[0].content == "解释器怎样运行程序？"
    assert "解释器怎样运行程序" in context.retrieval_query
