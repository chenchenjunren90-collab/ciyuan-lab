"""Evaluate lexical or pgvector retrieval against the checked-in dataset."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.core.database import create_database_engine
from app.modules.course_content import CoursePackRepository
from app.modules.rag.evaluation import evaluate_retriever, load_eval_cases
from app.modules.rag.pgvector_retriever import PgVectorKnowledgeRetriever
from app.modules.rag.ports import KnowledgeRetriever
from app.modules.rag.retriever import LexicalKnowledgeRetriever

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("lexical", "pgvector"), default="lexical")
    parser.add_argument("--dataset", type=Path, default=Path("evals/rag/retrieval-v1.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    courses = CoursePackRepository()
    retriever: KnowledgeRetriever
    if args.backend == "pgvector":
        retriever = PgVectorKnowledgeRetriever(create_database_engine(get_settings().database_url))
    else:
        retriever = LexicalKnowledgeRetriever.from_repository(courses)
    result = asyncio.run(evaluate_retriever(retriever, load_eval_cases(dataset)))
    payload = result.to_json()
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(f"Wrote evaluation report -> {output.relative_to(ROOT)}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
