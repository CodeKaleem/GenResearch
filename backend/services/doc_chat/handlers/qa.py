from __future__ import annotations

from services.rag_service import generate_answer, generate_answer_stream


async def handle_qa(user_id: str, query: str, *, top_k: int = 5, paper_id: str | None = None, exclude_references: bool = False):
    return await generate_answer(user_id=user_id, query=query, top_k=top_k, paper_id=paper_id, exclude_references=exclude_references)


async def handle_qa_stream(user_id: str, query: str, *, top_k: int = 5, paper_id: str | None = None, exclude_references: bool = False):
    async for item in generate_answer_stream(user_id=user_id, query=query, top_k=top_k, paper_id=paper_id, exclude_references=exclude_references):
        yield item
