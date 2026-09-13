"""Bounded online retrieval from the official Python documentation.

The retriever never follows arbitrary links and never sends a learner's full
question to a third-party search engine.  It ranks a fixed catalogue locally,
downloads at most a few pages from docs.python.org, and extracts only the
paragraphs that overlap the Python question.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import time
from collections import Counter, OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.modules.rag.ports import KnowledgeRetriever, SearchHit
from app.modules.rag.retriever import query_variants, tokenize


@dataclass(frozen=True, slots=True)
class _DocTarget:
    path: str
    title: str
    markers: tuple[str, ...]


_DOC_TARGETS = (
    _DocTarget(
        "reference/lexical_analysis.html",
        "词法分析与字符串字面值",
        ("f-string", "fstring", "字面值", "转义", "token", "缩进", "注释"),
    ),
    _DocTarget(
        "reference/expressions.html",
        "表达式",
        ("表达式", "海象", ":=", "切片", "解包", "推导式", "运算符", "lambda", "await", "yield"),
    ),
    _DocTarget(
        "reference/simple_stmts.html",
        "简单语句",
        (
            "return",
            "raise",
            "import",
            "global",
            "nonlocal",
            "assert",
            "del",
            "pass",
            "break",
            "continue",
        ),
    ),
    _DocTarget(
        "reference/compound_stmts.html",
        "复合语句",
        ("match", "case", "模式匹配", "if", "while", "for", "try", "with", "async", "class", "def"),
    ),
    _DocTarget(
        "reference/datamodel.html",
        "数据模型",
        ("数据模型", "__slots__", "魔术方法", "特殊方法", "可变", "不可变", "对象", "属性"),
    ),
    _DocTarget(
        "reference/import.html",
        "导入系统",
        ("导入系统", "importlib", "相对导入", "绝对导入", "模块搜索", "包"),
    ),
    _DocTarget(
        "tutorial/appetite.html",
        "Python 简介（开胃菜）",
        ("特点", "特性", "优势", "介绍", "是什么", "解释型", "编译", "语言", "开胃菜"),
    ),
    _DocTarget(
        "tutorial/introduction.html",
        "Python 入门",
        ("print", "input", "数字", "字符串", "列表", "入门", "特点", "特性", "优势", "介绍"),
    ),
    _DocTarget(
        "tutorial/controlflow.html",
        "流程控制",
        ("控制流", "range", "enumerate", "循环", "函数参数", "默认参数", "关键字参数",
         "边界控制", "循环终止", "端点"),
    ),
    _DocTarget(
        "tutorial/datastructures.html",
        "数据结构",
        ("列表", "元组", "集合", "字典", "队列", "栈", "zip", "sorted"),
    ),
    _DocTarget("tutorial/modules.html", "模块", ("模块", "包", "from", "__name__", "命名空间")),
    _DocTarget(
        "tutorial/inputoutput.html",
        "输入与输出",
        ("输入输出", "格式化", "format", "文件", "open", "read", "write", "json"),
    ),
    _DocTarget(
        "tutorial/errors.html",
        "错误与异常",
        ("异常", "报错", "traceback", "except", "finally", "raise"),
    ),
    _DocTarget(
        "tutorial/classes.html",
        "类与面向对象",
        ("面向对象", "继承", "多态", "class", "self", "闭包", "作用域", "迭代器", "生成器"),
    ),
    _DocTarget(
        "library/functions.html",
        "内置函数",
        (
            "内置函数",
            "all",
            "any",
            "sum",
            "min",
            "max",
            "map",
            "filter",
            "len",
            "type",
            "isinstance",
        ),
    ),
    _DocTarget(
        "library/stdtypes.html",
        "内置类型",
        ("内置类型", "str", "list", "tuple", "set", "dict", "bytes", "frozenset",
         "索引", "越界", "indexerror", "边界"),
    ),
    _DocTarget("library/dataclasses.html", "dataclasses", ("dataclass", "dataclasses", "数据类")),
    _DocTarget(
        "library/typing.html",
        "类型标注",
        ("typing", "类型标注", "类型提示", "annotation", "generic", "protocol"),
    ),
    _DocTarget(
        "library/asyncio.html", "异步编程", ("asyncio", "异步", "协程", "async", "await", "task")
    ),
    _DocTarget("library/pathlib.html", "pathlib 路径", ("pathlib", "path", "路径", "目录")),
    _DocTarget("library/re.html", "正则表达式", ("正则", "re", "regex", "match", "search")),
)

_SKIP_TAGS = {"script", "style", "svg", "nav", "footer", "noscript"}
_BLOCK_TAGS = {"p", "pre", "dt", "li"}

# Characteristic phrases for "what is Python / its features" questions,
# weighted by how directly they describe the language itself.
_FEATURE_BLOCK_MARKERS: dict[str, float] = {
    "解释型": 0.50,
    "面向对象": 0.50,
    "简洁": 0.40,
    "易读": 0.40,
    "强大": 0.35,
    "高级": 0.30,
    "动态": 0.30,
    "缩进": 0.25,
    "开源": 0.25,
    "可移植": 0.25,
    "模块": 0.15,
}


class _ReadableBlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._skip_depth = 0
        self._capture_tag: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth == 0 and tag in _BLOCK_TAGS and self._capture_tag is None:
            self._capture_tag = tag
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth == 0 and tag == self._capture_tag:
            text = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
            if 20 <= len(text) <= 2_000:
                self.blocks.append(text)
            self._capture_tag = None
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and self._capture_tag is not None and data.strip():
            self._parts.append(data.strip())


class PythonOfficialDocsRetriever(KnowledgeRetriever):
    """Search a small allowlisted catalogue of Python 3.11 Chinese docs."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        base_url: str = "https://docs.python.org/zh-cn/3.11/",
        timeout_seconds: float = 8.0,
        max_pages: int = 2,
        client: httpx.AsyncClient | None = None,
        cache_ttl_seconds: float = 3600,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.hostname != "docs.python.org":
            raise ValueError("Python documentation base URL must be https://docs.python.org")
        self._enabled = enabled
        self._base_url = base_url.rstrip("/") + "/"
        self._timeout_seconds = timeout_seconds
        self._max_pages = max(1, min(max_pages, 3))
        self._client = client
        self._cache_ttl = max(0, cache_ttl_seconds)
        self._cache: OrderedDict[str, tuple[float, tuple[str, ...]]] = OrderedDict()
        self._query_cache: OrderedDict[str, tuple[float, tuple[SearchHit, ...]]] = OrderedDict()
        self._page_locks: dict[str, asyncio.Lock] = {}

    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        if not self._enabled or course_id != "python" or top_k < 1 or not query.strip():
            return ()
        key = hashlib.sha256(f"{top_k}:{query.strip().casefold()}".encode()).hexdigest()
        cached = self._query_cache.get(key)
        if cached is not None and cached[0] > time.monotonic():
            self._query_cache.move_to_end(key)
            return cached[1]
        ranked_targets = self._rank_targets(query)[: self._max_pages]
        if not ranked_targets:
            return ()
        pages = await asyncio.gather(
            *(self._load_target(target) for _, target in ranked_targets),
            return_exceptions=True,
        )
        ranked: list[tuple[float, _DocTarget, str, str]] = []
        for (target_score, target), result in zip(ranked_targets, pages, strict=True):
            if isinstance(result, BaseException):
                continue
            url, blocks = result
            ranked.extend(
                (
                    # Page selection is not paragraph relevance. A large page
                    # bonus used to saturate all scores and sort by text instead.
                    min(0.99, score + min(0.12, target_score / 100)),
                    target,
                    url,
                    block,
                )
                for score, block in self._rank_blocks(query, blocks)[:2]
            )
        ranked.sort(key=lambda item: (-item[0], item[1].path, item[3]))
        hits = tuple(self._to_hit(*item) for item in ranked[:top_k])
        # Cache only public evidence, never generated dialogue or student identities.
        # Short negative TTL allows a recovered network/updated source to be retried.
        ttl = min(self._cache_ttl, 300 if hits else 15)
        self._query_cache[key] = (time.monotonic() + ttl, hits)
        self._query_cache.move_to_end(key)
        while len(self._query_cache) > 128:
            self._query_cache.popitem(last=False)
        return hits

    def _rank_targets(self, query: str) -> list[tuple[float, _DocTarget]]:
        normalized = query.casefold()
        query_terms = tokenize(query)
        list_concatenation = _is_list_concatenation_query(normalized)
        ranked: list[tuple[float, _DocTarget]] = []
        for target in _DOC_TARGETS:
            score = self._overlap(
                query_terms, tokenize(f"{target.title} {' '.join(target.markers)}")
            )
            for marker in target.markers:
                if marker.casefold() in normalized:
                    score += 3.0 + min(len(marker), 12) / 12
            if "边界控制" in normalized and target.path in {
                "tutorial/controlflow.html", "library/stdtypes.html",
            }:
                score += 12.0
            if list_concatenation and target.path == "library/stdtypes.html":
                score += 18.0
            elif list_concatenation and target.path == "tutorial/introduction.html":
                score += 8.0
            if score > 0:
                ranked.append((score, target))
        ranked.sort(key=lambda item: (-item[0], item[1].path))
        return ranked

    async def _load_target(self, target: _DocTarget) -> tuple[str, tuple[str, ...]]:
        url = urljoin(self._base_url, target.path)
        # The catalogue is fixed, so this lock map is bounded by catalogue size.
        async with self._page_locks.setdefault(url, asyncio.Lock()):
            return await self._load_page(url)

    async def _load_page(self, url: str) -> tuple[str, tuple[str, ...]]:
        cached = self._cache.get(url)
        if cached is not None and cached[0] > time.monotonic():
            self._cache.move_to_end(url)
            return url, cached[1]
        if self._client is not None:
            response = await self._client.get(url, follow_redirects=False)
        else:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(url, follow_redirects=False)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type.casefold() or len(response.content) > 1_500_000:
            raise ValueError("unexpected Python documentation response")
        parser = _ReadableBlockParser()
        # docs.python.org pages declare UTF-8 in HTML, but some responses omit
        # the HTTP charset; httpx would otherwise guess an incompatible codec.
        parser.feed(response.content.decode("utf-8", errors="strict"))
        blocks = tuple(dict.fromkeys(parser.blocks))
        self._cache[url] = (time.monotonic() + self._cache_ttl, blocks)
        self._cache.move_to_end(url)
        while len(self._cache) > 64:
            self._cache.popitem(last=False)
        return url, blocks

    def _rank_blocks(self, query: str, blocks: Sequence[str]) -> list[tuple[float, str]]:
        if "边界控制" in query:
            query += " range 起点 终点 终止值 索引"
        list_concatenation = _is_list_concatenation_query(query.casefold())
        if list_concatenation:
            query += " 列表 序列 拼接 连接 相同类型序列 +"
        variants = query_variants(query)
        query_terms = [tokenize(item) for item in variants if item.strip()]
        example_requested = any(
            marker in query.casefold()
            for marker in ("例子", "示例", "代码", "怎么写", "如何写", "example")
        )
        # Broad "what is Python / its features" questions must prefer prose
        # explanations over incidental code snippets that merely share the
        # token "python".
        feature_intent = any(
            marker in query for marker in ("特点", "特性", "优势", "介绍", "是什么", "入门")
        )
        boundary_intent = any(
            marker in query.casefold()
            for marker in ("边界", "越界", "端点", "终止", "indexerror")
        )
        ranked: list[tuple[float, str]] = []
        for block in blocks:
            block_terms = tokenize(block)
            score = max((self._overlap(terms, block_terms) for terms in query_terms), default=0.0)
            if score <= 0:
                continue
            if not example_requested and (
                block.lstrip().startswith((">>>", "class ")) or len(block) < 40
            ):
                score *= 0.25
            if boundary_intent and "async" in block and "async" not in query.casefold():
                score *= 0.1
            if boundary_intent and any(
                marker in block.casefold() for marker in ("range", "索引", "indexerror", "循环")
            ) and any(
                marker in block.casefold()
                for marker in ("不包含", "不包括", "不会包括", "超出", "终止", "stop", "indexerror")
            ) and not block.lstrip().startswith((">>>", "class ")):
                score += 1.0
            if list_concatenation and any(
                marker in block.casefold() for marker in ("拼接", "连接", "concaten", " s + t")
            ) and any(marker in block.casefold() for marker in ("列表", "list", "序列")):
                score += 1.4
            if feature_intent:
                if "编程语言" in block or "语言" in block:
                    score += 0.30
                feature_bonus = sum(
                    weight
                    for marker, weight in _FEATURE_BLOCK_MARKERS.items()
                    if marker in block
                )
                if feature_bonus:
                    score += min(0.70, feature_bonus)
                if block.strip().startswith(">>>") or block.count(">>>") >= 2:
                    score *= 0.45
            code_bonus = (
                0.20
                if example_requested
                and any(marker in block for marker in (">>>", "...", " = ", "print(", "def "))
                else 0.0
            )
            ranked.append((min(0.99, 0.45 + score / 4 + code_bonus), block[:900]))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[:3]

    @staticmethod
    def _overlap(left: Counter[str], right: Counter[str]) -> float:
        numerator = sum(min(count, right.get(term, 0)) for term, count in left.items())
        if numerator <= 0:
            return 0.0
        left_norm = math.sqrt(sum(count * count for count in left.values()))
        right_norm = math.sqrt(sum(count * count for count in right.values()))
        return numerator / max(left_norm * right_norm, 1.0)

    @staticmethod
    def _to_hit(score: float, target: _DocTarget, url: str, content: str) -> SearchHit:
        source_suffix = re.sub(r"[^A-Z0-9]+", "-", target.path.upper()).strip("-")
        source_id = f"WEB-PYDOC-{source_suffix}"
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
        return SearchHit(
            source_id=source_id,
            chunk_id=f"{source_id}-{digest}",
            content=content,
            score=round(score, 6),
            metadata={
                "source_type": "online",
                "title": target.title,
                "url": url,
                "publisher": "Python Software Foundation",
                "version": "3.11",
            },
        )


def _is_list_concatenation_query(query: str) -> bool:
    compact = re.sub(r"\s+", "", query)
    return (
        ("[" in compact and "]" in compact and "+" in compact)
        or (
            "列表" in compact
            and any(marker in compact for marker in ("相加", "拼接", "连接", "+"))
        )
    )
