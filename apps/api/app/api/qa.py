"""RAG question-answering endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_course_repository, get_rag_qa_service
from app.modules.course_content import CourseRecordNotFoundError
from app.modules.rag.models import QaRequest, QaResponse
from app.modules.rag.service import RagQaService

router = APIRouter(tags=["qa"])


@router.post("/qa", response_model=QaResponse)
async def ask_question(
    request: QaRequest,
    service: Annotated[RagQaService, Depends(get_rag_qa_service)],
) -> QaResponse:
    if request.knowledge_point_id is not None:
        try:
            point = get_course_repository().get_knowledge_point(
                request.course_id, request.knowledge_point_id
            )
        except CourseRecordNotFoundError as exc:
            raise HTTPException(status_code=404, detail="未找到本课程的知识点。") from exc
        return await service.answer(
            course_id=request.course_id, question=request.question,
            source_scope=frozenset(point.source_refs),
        )
    return await service.answer(course_id=request.course_id, question=request.question)
