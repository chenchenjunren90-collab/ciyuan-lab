"""Classroom social-turn classification and in-role replies."""

from __future__ import annotations

from app.modules.orchestration.classroom import _SOCIAL_REPLIES, _is_social_message


def test_thanks_without_technical_content_is_social() -> None:
    assert _is_social_message("谢谢老师")
    assert _is_social_message("谢谢")
    assert _is_social_message("辛苦了")
    assert _is_social_message("加油")


def test_short_confirmations_keep_the_contextual_flow() -> None:
    # Confirmations such as 好的/明白了 continue the previous example and must
    # NOT be swallowed by the social short-circuit.
    assert not _is_social_message("好的")
    assert not _is_social_message("明白了")
    assert not _is_social_message("收到")


def test_social_markers_with_technical_content_are_not_social() -> None:
    assert not _is_social_message("好的，那for循环呢")
    assert not _is_social_message("谢谢，再讲讲列表")
    assert not _is_social_message("else后可以加括号吗")
    assert not _is_social_message("如果加括号会报错吗")


def test_non_social_questions_keep_normal_flow() -> None:
    assert not _is_social_message("列表推导式怎么写")
    assert not _is_social_message("这个报错是什么意思")


def test_social_replies_exist_for_every_classroom_role() -> None:
    for role in ("teacher", "ta", "peer_cautious", "peer_debugger", "peer_summarizer"):
        assert _SOCIAL_REPLIES[role].strip()
