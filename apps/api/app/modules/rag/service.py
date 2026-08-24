"""Evidence-first RAG application service."""

from app.modules.course_content import CourseId
from app.modules.rag.models import Citation, QaResponse
from app.modules.rag.ports import KnowledgeRetriever


class RagQaService:
    def __init__(self, retriever: KnowledgeRetriever, *, top_k: int = 3) -> None:
        self._retriever = retriever
        self._top_k = top_k

    async def answer(self, *, course_id: CourseId, question: str) -> QaResponse:
        hits = await self._retriever.search(question, course_id, self._top_k)
        if not hits:
            return QaResponse(status="insufficient_evidence", answer="", citations=[])
        evidence = "\n".join(
            f"{index}. {hit.content}" for index, hit in enumerate(hits, start=1)
        )
        return QaResponse(
            status="answered",
            answer=f"根据已审核课程资料，可得到以下相关依据：\n{evidence}",
            citations=[
                Citation(
                    source_id=hit.source_id,
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                )
                for hit in hits
            ],
        )
