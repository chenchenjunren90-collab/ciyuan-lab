"""Evidence-first RAG application service."""

from app.modules.course_content import CourseId
from app.modules.orchestration.supervisor import QualitySupervisor
from app.modules.orchestration.tutor import CourseTutor
from app.modules.rag.models import Citation, QaResponse
from app.modules.rag.ports import KnowledgeRetriever


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
        hits = await self._retriever.search(question, course_id, self._top_k)
        if not hits:
            return QaResponse(status="insufficient_evidence", answer="", citations=[])
        draft = await self._tutor.draft(question=question, evidence=hits)
        decision = self._supervisor.inspect(draft=draft, evidence=hits)
        if not decision.accepted:
            return QaResponse(status="insufficient_evidence", answer="", citations=[])
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
        )
