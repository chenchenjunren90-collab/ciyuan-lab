"""RAG question-answering endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_rag_qa_service
from app.modules.rag.models import QaRequest, QaResponse
from app.modules.rag.service import RagQaService

router = APIRouter(tags=["qa"])


@router.post("/qa", response_model=QaResponse)
async def ask_question(
    request: QaRequest,
    service: Annotated[RagQaService, Depends(get_rag_qa_service)],
) -> QaResponse:
    return await service.answer(course_id=request.course_id, question=request.question)
