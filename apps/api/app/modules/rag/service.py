"""Evidence-first RAG application service."""

from __future__ import annotations

import re

from app.modules.course_content import CourseId
from app.modules.orchestration.supervisor import QualitySupervisor
from app.modules.orchestration.tutor import CourseTutor
from app.modules.rag.citations import citation_from_hit
from app.modules.rag.models import AgentTraceStep, Citation, QaResponse
from app.modules.rag.ports import KnowledgeRetrievalError, KnowledgeRetriever, SearchHit
from app.modules.rag.question_gates import is_prompt_injection, supplement_gate_passes
from app.modules.rag.retriever import query_is_in_course_scope

# A best-hit below this floor is treated as "almost no evidence" and may
# trigger the controlled online supplement for the Python course.
_WEAK_HIT_SCORE_FLOOR = 0.15

_SUPPLEMENT_NOTICE = (
    "\n\n[来源说明] 当前课程资料库暂未收录该内容；以上信息来自 Python 官方文档，"
    "已标记为待审核入库补充。"
)


class RagQaService:
    def __init__(
        self,
        retriever: KnowledgeRetriever,
        tutor: CourseTutor,
        supervisor: QualitySupervisor,
        *,
        top_k: int = 3,
        online_retriever: KnowledgeRetriever | None = None,
        supplement_enabled: bool = True,
    ) -> None:
        self._retriever = retriever
        self._tutor = tutor
        self._supervisor = supervisor
        self._top_k = top_k
        self._online_retriever = online_retriever
        self._supplement_enabled = supplement_enabled

    async def answer(self, *, course_id: CourseId, question: str) -> QaResponse:
        # Deterministic security gate runs before ANY retrieval: attempts to
        # extract protected information never reach the index, the model or
        # the online supplement.
        if is_prompt_injection(question):
            return QaResponse(
                status="insufficient_evidence",
                answer="该问题涉及受保护信息，已按安全规则拒绝处理。",
                citations=[],
                trace=[
                    AgentTraceStep(
                        component="retrieval",
                        status="blocked",
                        detail="安全门禁拦截：检测到对受保护信息的索取。",
                    )
                ],
            )
        try:
            hits = await self._retriever.search(question, course_id, self._top_k)
        except KnowledgeRetrievalError:
            return QaResponse(
                status="insufficient_evidence",
                answer="课程资料检索暂时不可用，请稍后重试。",
                citations=[],
                trace=[
                    AgentTraceStep(
                        component="retrieval",
                        status="degraded",
                        detail="知识索引连接或查询失败，未调用模型生成无依据的回答。",
                    )
                ],
            )
        weak_hits = bool(hits) and max(hit.score for hit in hits) < _WEAK_HIT_SCORE_FLOOR
        if not hits or weak_hits:
            supplement = await self._maybe_supplement(course_id=course_id, question=question)
            if supplement is not None:
                return supplement
        if not hits:
            return QaResponse(
                status="insufficient_evidence",
                answer="",
                citations=[],
                trace=[
                    AgentTraceStep(
                        component="retrieval",
                        status="blocked",
                        detail="当前课程的已审核资料未检索到足够证据。",
                    )
                ],
            )
        draft = await self._tutor.draft(question=question, evidence=hits, course_id=course_id)
        decision = await self._supervisor.review(
            draft=draft,
            evidence=hits,
            learning_context=f"{course_id} 课程问答：{question}",
        )
        trace = [
            AgentTraceStep(
                component="retrieval",
                status="completed",
                detail=f"在当前课程内找到 {len(hits)} 条候选证据。",
            ),
            AgentTraceStep(
                component="course_tutor",
                status="degraded" if draft.degraded else "completed",
                detail=(
                    "模型不可用或输出不合规，已使用证据摘录安全降级。"
                    if draft.degraded
                    else "已基于候选证据组织回答草稿。"
                ),
            ),
        ]
        rerank_statuses = {hit.metadata.get("rerank_status") for hit in hits}
        if "degraded" in rerank_statuses:
            trace.insert(
                1,
                AgentTraceStep(
                    component="retrieval",
                    status="degraded",
                    detail="语义重排暂不可用，已保留原始课程证据检索结果。",
                ),
            )
        elif "completed" in rerank_statuses:
            trace.insert(
                1,
                AgentTraceStep(
                    component="retrieval",
                    status="completed",
                    detail="已通过讯飞 MaaS 对候选课程证据进行语义重排。",
                ),
            )
        if not decision.accepted:
            unavailable = decision.model_degraded
            trace.append(
                AgentTraceStep(
                    component="quality_supervisor",
                    status="degraded" if unavailable else "blocked",
                    detail=(
                        "质量审核暂时不可用，回答草稿未发布。"
                        if unavailable
                        else f"质量门禁未通过：{decision.reason_code}。"
                    ),
                )
            )
            return QaResponse(
                status="insufficient_evidence",
                answer="质量审核暂时不可用，请稍后重试。" if unavailable else "",
                citations=[],
                trace=trace,
            )
        trace.append(
            AgentTraceStep(
                component="quality_supervisor",
                status="degraded" if decision.model_degraded else "completed",
                detail=(
                    "模型语义审核暂不可用；确定性引用与安全门禁检查通过。"
                    if decision.model_degraded
                    else (
                        "模型语义审核与确定性引用、安全门禁均已通过。"
                        if decision.model_reviewed
                        else "确定性引用、内容长度与安全门禁检查通过。"
                    )
                ),
            )
        )
        return QaResponse(
            status="answered",
            answer=decision.answer,
            citations=[
                Citation(
                    source_id=hit.source_id,
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                    source_title=(
                        str(title)[:200]
                        if isinstance(title := hit.metadata.get("title"), str)
                        else None
                    ),
                )
                for hit in decision.citations
            ],
            trace=trace,
        )

    async def _maybe_supplement(
        self, *, course_id: CourseId, question: str
    ) -> QaResponse | None:
        """Controlled online supplement for an uncovered Python question.

        Runs only when every deterministic gate passes and a configured online
        retriever is present. Any failure returns ``None`` so the caller falls
        back to the ordinary blocked/weak-evidence path; the supplement can
        never widen what the caller publishes.
        """
        if not self._supplement_enabled or self._online_retriever is None:
            return None
        if course_id != "python":
            return None
        if not query_is_in_course_scope(question, course_id):
            return None
        if not supplement_gate_passes(question):
            return None
        try:
            online_hits = await self._online_retriever.search(question, "python", 3)
        except KnowledgeRetrievalError:
            return None
        if not online_hits:
            # The docs catalogue is the relevance signal; a transient fetch
            # failure returns an empty list, so allow one bounded retry.
            try:
                online_hits = await self._online_retriever.search(question, "python", 3)
            except KnowledgeRetrievalError:
                return None
        if not online_hits:
            return None
        review = await self._supervisor.review_knowledge_gap(
            question=question,
            evidence=online_hits,
            learning_context="python 课程问答（课程资料库证据不足）",
        )
        if not review.relevant or not review.answer or not review.used_chunk_ids:
            return None
        by_chunk = {hit.chunk_id: hit for hit in online_hits}
        used_hits: list[SearchHit] = []
        for chunk_id in review.used_chunk_ids:
            hit = by_chunk.get(chunk_id)
            if hit is None or re.search(r"(?i)api[_ -]?key\s*[:=]", hit.content):
                return None
            used_hits.append(hit)
        if not used_hits:
            return None
        answer = f"{review.answer}{_SUPPLEMENT_NOTICE}"
        return QaResponse(
            status="answered",
            answer=answer,
            citations=[citation_from_hit(hit) for hit in used_hits],
            trace=[
                AgentTraceStep(
                    component="retrieval",
                    status="blocked",
                    detail="当前课程的已审核资料未检索到足够证据，已按规则触发受控补充研判。",
                ),
                AgentTraceStep(
                    component="quality_supervisor",
                    status="completed",
                    detail=(
                        "监督智能体结合课程上下文与 Python 官方文档完成缺口研判："
                        "确认问题相关并补充回答，内容已标注为待审核入库。"
                    ),
                ),
            ],
        )
