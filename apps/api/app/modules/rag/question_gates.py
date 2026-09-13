"""Deterministic question gates for the knowledge-gap supplement path.

These gates decide — WITHOUT asking the language model to police itself —
whether a question with no course-base evidence may enter the controlled
online-supplement flow. The same markers are mirrored in the classroom
question classifiers (``orchestration/classroom.py``); this module keeps the
RAG layer independent of orchestration.
"""

from __future__ import annotations

import re

_CODE_IDENTIFIER = re.compile(r"(?i)(?<![a-z0-9_])([a-z_][a-z0-9_]*)(?![a-z0-9_])")

_PYTHON_RELEVANCE_IDENTIFIERS = frozenset(
    {
        "print",
        "input",
        "int",
        "float",
        "str",
        "bool",
        "list",
        "tuple",
        "set",
        "dict",
        "for",
        "if",
        "elif",
        "else",
        "while",
        "break",
        "continue",
        "range",
        "len",
        "append",
        "get",
        "keys",
        "values",
        "items",
        "def",
        "return",
        "lambda",
        "import",
        "from",
        "try",
        "except",
        "finally",
        "class",
        "self",
        "open",
        "read",
        "write",
        "with",
        "yield",
        "next",
        "iter",
        "enumerate",
        "zip",
        "map",
        "filter",
        "sorted",
        "match",
        "case",
        "async",
        "await",
        "assert",
        "pass",
        "raise",
        "global",
        "nonlocal",
        "dataclass",
    }
)

_PYTHON_WEB_MARKERS = (
    "python",
    "python3",
    "语法",
    "代码报错",
    "traceback",
    ".py",
    "列表推导式",
    "字典推导式",
    "海象运算符",
    "模式匹配",
    "类型标注",
    "异步编程",
    "协程",
    "正则表达式",
    "dataclass",
    "__slots__",
    "pip",
    "venv",
)

_PYTHON_RELEVANCE_TERMS = frozenset(
    {
        "解释器",
        "输入",
        "输出",
        "变量",
        "类型",
        "运算",
        "条件",
        "循环",
        "字符串",
        "列表",
        "元组",
        "集合",
        "字典",
        "键值",
        "函数",
        "参数",
        "返回",
        "迭代",
        "模块",
        "文件",
        "异常",
        "对象",
        "指针",
        "内存",
        "结构体",
        "编译",
        "链表",
        "栈",
        "队列",
        "树",
        "图",
        "哈希",
        "散列",
        "复杂度",
        "遍历",
        "查找",
        "排序",
        "递归",
        "生成器",
        "装饰器",
        "上下文管理器",
        "列表推导式",
        "字典推导式",
    }
)

_EXPLICIT_OFF_TOPIC_MARKERS = (
    "java",
    "javascript",
    "typescript",
    "c++",
    "golang",
    "rust",
    "html",
    "css",
    "sql",
    "今天天气",
    "天气预报",
    "新闻",
    "股票",
    "医疗诊断",
    "法律咨询",
    "写作文",
    "翻译成英语",
    "电影推荐",
    "旅游攻略",
    "勾股定理",
)

_PROTECTED_TARGETS = (
    "system prompt",
    "系统提示",
    "api key",
    "apikey",
    "api_key",
    "密钥",
    "密码",
    "令牌",
)
_OVERRIDE_SIGNALS = ("忽略", "覆盖规则", "无视规则", "泄露", "输出", "告诉我")

# Questions longer than this are unlikely to be single-concept gaps.
_MAX_SUPPLEMENT_QUESTION_CHARS = 200


def is_prompt_injection(message: str) -> bool:
    normalized = re.sub(r"\s+", " ", message.casefold())
    return any(target in normalized for target in _PROTECTED_TARGETS) and any(
        signal in normalized for signal in _OVERRIDE_SIGNALS
    )


def is_explicit_off_topic_question(message: str) -> bool:
    normalized = re.sub(r"\s+", "", message.casefold())
    return any(marker in normalized for marker in _EXPLICIT_OFF_TOPIC_MARKERS)


def has_python_technical_signal(message: str) -> bool:
    """Require an affirmative Python/programming signal before supplementing."""
    normalized = message.casefold()
    identifiers = {
        item.casefold() for item in _CODE_IDENTIFIER.findall(message)
    }
    return bool(
        identifiers & _PYTHON_RELEVANCE_IDENTIFIERS
        or any(marker in normalized for marker in _PYTHON_WEB_MARKERS)
        or any(term in message for term in _PYTHON_RELEVANCE_TERMS)
    )


def supplement_gate_passes(question: str) -> bool:
    """Deterministic pre-conditions for entering the online supplement.

    Relevance itself is NOT decided here: the allowlisted Python documentation
    catalogue and the supervisor's review carry that judgment. These gates only
    filter out requests that must never reach any retrieval: prompt injection,
    explicit off-topic topics and malformed lengths.
    """
    stripped = question.strip()
    if not 2 <= len(stripped) <= _MAX_SUPPLEMENT_QUESTION_CHARS:
        return False
    if is_prompt_injection(stripped):
        return False
    return not is_explicit_off_topic_question(stripped)
