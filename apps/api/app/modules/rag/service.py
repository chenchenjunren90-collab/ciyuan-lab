"""Evidence-first RAG application service."""

from app.modules.course_content import CourseId
from app.modules.orchestration.supervisor import QualitySupervisor
from app.modules.orchestration.tutor import CourseTutor
from app.modules.rag.models import AgentTraceStep, Citation, QaResponse
from app.modules.rag.ports import KnowledgeRetrievalError, KnowledgeRetriever


class RagQaService:
    def __init__(
        self,
        retriever: KnowledgeRetriever,
        tutor: CourseTutor,
        supervisor: QualitySupervisor,
        *,
        top_k: int = 3,
    ) -> None:
        self._retriever = retriever
        self._tutor = tutor
        self._supervisor = supervisor
        self._top_k = top_k

    async def answer(self, *, course_id: CourseId, question: str) -> QaResponse:
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
                )
                for hit in decision.citations
            ],
            trace=trace,
        )
