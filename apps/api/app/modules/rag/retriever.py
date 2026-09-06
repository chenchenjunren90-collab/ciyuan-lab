"""Deterministic, course-isolated retrieval for the offline MVP."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.modules.course_content import CourseId, CoursePackRepository, RagSourceRecord
from app.modules.rag.ports import KnowledgeRetriever, SearchHit

ASCII_WORD = re.compile(r"[a-z0-9_+#.-]+")
CODE_IDENTIFIER = re.compile(r"(?i)(?<![a-z0-9_])([a-z_][a-z0-9_]*)(?![a-z0-9_])")
CJK_RUN = re.compile(r"[\u3400-\u9fff]+")

_QUERY_IDENTIFIER_STOP_WORDS = frozenset(
    {"python", "language", "code", "program", "please", "help"}
)

_CJK_TECHNICAL_QUERY_TERMS = (
    "解释器",
    "输入",
    "输出",
    "变量",
    "类型",
    "运算符",
    "条件",
    "循环",
    "字符串",
    "数组",
    "列表",
    "元组",
    "集合",
    "字典",
    "键值",
    "函数",
    "参数",
    "返回值",
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
    "权重",
    "最短路",
    "生成器",
    "装饰器",
    "上下文管理器",
)

_COURSE_SCOPE_MARKERS: dict[str, tuple[str, ...]] = {
    "c": (
        "c语言",
        "c程序",
        "c字符串",
        "c头文件",
        "printf",
        "scanf",
        "malloc",
        "calloc",
        "realloc",
        "空字符",
        "预处理",
    ),
    "python": (
        "python",
        "生成器",
        "列表推导式",
        "字典推导式",
        "上下文管理器",
        "装饰器",
    ),
    "data_structures": (
        "数据结构",
        "bfs",
        "dfs",
        "dijkstra",
        "二分查找",
        "散列表",
        "哈希表",
        "邻接表",
        "最短路",
        "拓扑排序",
        "二叉树",
        "时间复杂度",
        "空间复杂度",
    ),
}


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    source_id: str
    chunk_id: str
    course_id: CourseId
    title: str
    citation: dict[str, object]
    content: str
    term_counts: Counter[str]


def tokenize(text: str) -> Counter[str]:
    """Tokenize mixed Chinese/programming text without an external segmenter."""

    normalized = text.casefold()
    tokens = ASCII_WORD.findall(normalized)
    for run in CJK_RUN.findall(normalized):
        # Keep the complete CJK run as one exact token. ``list.extend(run)``
        # would add every Han character separately and create false matches
        # between unrelated questions and evidence that merely share a common
        # character (for example ``民法典`` and ``算法`` both contain ``法``).
        tokens.append(run)
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    return Counter(token for token in tokens if token.strip())


def query_variants(
    text: str,
    *,
    max_clauses: int = 4,
    max_identifiers: int = 4,
    max_cjk_terms: int = 4,
) -> tuple[str, ...]:
    """Return the complete question plus bounded sentence-level subqueries.

    A compound student question can mention two related concepts. Scoring only
    the complete text dilutes the overlap of each relevant evidence chunk. The
    retrievers therefore score the full question and a small, deterministic set
    of clauses, then keep the best score per chunk.  Code identifiers are also
    emitted independently: otherwise a short identifier such as ``print`` can
    be diluted by a long natural-language sentence in the lexical backend.
    """

    normalized = text.strip()
    if not normalized:
        return ()
    variants = [normalized]
    for clause in re.split(r"[。！？!?；;\n]+", normalized):
        clause = clause.strip(" ，,：:")
        if len(clause) >= 2 and clause not in variants:
            variants.append(clause)
        if len(variants) >= max_clauses + 1:
            break
    identifiers: list[str] = []
    for match in CODE_IDENTIFIER.finditer(normalized):
        identifier = match.group(1).casefold()
        if (
            len(identifier) >= 2
            and identifier not in _QUERY_IDENTIFIER_STOP_WORDS
            and identifier not in identifiers
        ):
            identifiers.append(identifier)
        if len(identifiers) >= max_identifiers:
            break
    variants.extend(identifier for identifier in identifiers if identifier not in variants)
    cjk_terms = sorted(
        (term for term in _CJK_TECHNICAL_QUERY_TERMS if term in normalized),
        key=lambda term: (normalized.find(term), -len(term)),
    )[:max_cjk_terms]
    variants.extend(term for term in cjk_terms if term not in variants)
    return tuple(variants)


def query_is_in_course_scope(text: str, course_id: str) -> bool:
    """Reject only questions that explicitly target another supported course.

    Generic programming terms are intentionally absent from the marker table.
    When a question has no unambiguous course marker, retrieval evidence and the
    normal score threshold still decide whether it can be answered.
    """

    normalized = re.sub(r"\s+", "", text.casefold())
    mentioned = {
        candidate
        for candidate, markers in _COURSE_SCOPE_MARKERS.items()
        if any(marker in normalized for marker in markers)
    }
    return not mentioned or course_id in mentioned


def split_source(source: RagSourceRecord, *, max_chars: int = 360) -> Iterable[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", source.text) if part.strip()]
    for paragraph in paragraphs:
        sentences = [
            part.strip() for part in re.split(r"(?<=[。！？；])", paragraph) if part.strip()
        ]
        buffer = ""
        for sentence in sentences:
            if buffer and len(buffer) + len(sentence) > max_chars:
                yield buffer
                buffer = sentence
            else:
                buffer += sentence
        if buffer:
            yield buffer


class LexicalKnowledgeRetriever(KnowledgeRetriever):
    """Small deterministic index; the port can later be backed by pgvector."""

    def __init__(self, chunks: Sequence[IndexedChunk], *, min_score: float = 0.10) -> None:
        self._chunks = tuple(chunks)
        self._min_score = min_score

    @classmethod
    def from_repository(cls, courses: CoursePackRepository) -> LexicalKnowledgeRetriever:
        chunks: list[IndexedChunk] = []
        for course_id in ("c", "python", "data_structures"):
            for source in courses.list_rag_source_records(course_id):
                for index, content in enumerate(split_source(source), start=1):
                    digest = hashlib.sha256(content.encode()).hexdigest()[:10]
                    chunks.append(
                        IndexedChunk(
                            source_id=source.id,
                            chunk_id=f"{source.id}-{index:03d}-{digest}",
                            course_id=course_id,
                            title=source.title,
                            citation={str(key): value for key, value in source.citation.items()},
                            content=content,
                            term_counts=tokenize(f"{source.title} {content}"),
                        )
                    )
        return cls(chunks)

    async def search(self, query: str, course_id: str, top_k: int) -> Sequence[SearchHit]:
        if not query.strip() or top_k < 1 or not query_is_in_course_scope(query, course_id):
            return ()
        variants = query_variants(query)
        query_terms = tuple(filter(None, (tokenize(item) for item in variants)))
        if not query_terms:
            return ()
        exact_identifiers = {
            variant.casefold()
            for variant in variants
            if CODE_IDENTIFIER.fullmatch(variant)
            and variant.casefold() not in _QUERY_IDENTIFIER_STOP_WORDS
        }
        exact_cjk_terms = {variant for variant in variants if variant in _CJK_TECHNICAL_QUERY_TERMS}
        ranked: list[tuple[float, IndexedChunk]] = []
        for chunk in self._chunks:
            if chunk.course_id != course_id:
                continue
            score = max(self._cosine(terms, chunk.term_counts) for terms in query_terms)
            if any(chunk.term_counts.get(term, 0) for term in exact_identifiers):
                # A single programming identifier is often the strongest part
                # of a beginner's natural-language question.  Long source
                # chunks otherwise dilute its cosine score below min_score.
                score = max(score, 0.30 + min(score, 0.20))
            elif any(chunk.term_counts.get(term, 0) for term in exact_cjk_terms):
                # Preserve the original full-question ordering.  A flat boost
                # would tie every chunk mentioning a broad word such as
                # "异常" and could displace a more relevant data-quality hit.
                score = max(score, 0.12 + min(score, 0.25))
            if score >= self._min_score:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return tuple(
            SearchHit(
                source_id=chunk.source_id,
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                score=round(score, 6),
                metadata={"title": chunk.title, "citation": chunk.citation},
            )
            for score, chunk in ranked[: min(top_k, 10)]
        )

    @staticmethod
    def _cosine(left: Counter[str], right: Counter[str]) -> float:
        shared = set(left) & set(right)
        if not shared:
            return 0.0
        numerator = sum(left[token] * right[token] for token in shared)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0
