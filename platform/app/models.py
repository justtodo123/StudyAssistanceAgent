"""领域模型：知识块、检索请求/响应、问答请求/响应。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievalChunk(BaseModel):
    """知识库中的一个可检索切片（一篇文章或一个 `##` 小节），file 字段即出处。"""

    id: str = Field(description="稳定唯一 ID（文件路径 + 小节标题）")
    file: str = Field(description="知识库文件相对路径，作为回答时的出处")
    title: str = ""
    course: str = ""
    tags: list[str] = []
    difficulty: str = ""
    updated: str = ""
    content: str = ""
    score: float = 0.0


class SearchRequest(BaseModel):
    question: str
    top_k: int = 5
    course: str | None = None
    use_vector: bool = True


class SearchResponse(BaseModel):
    question: str
    mode: str  # hybrid | keyword-only
    results: list[RetrievalChunk]


class QaRequest(BaseModel):
    question: str
    top_k: int = 5
    course: str | None = None
    use_vector: bool = True
    use_llm: bool = False


class QaResponse(BaseModel):
    question: str
    answer: str
    mode: str
    sources: list[RetrievalChunk]
