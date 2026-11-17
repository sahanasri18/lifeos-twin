from pydantic import BaseModel, Field


class KnowledgeQuery(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=4, ge=1, le=10)


class KnowledgeIngest(BaseModel):
    id: str = Field(min_length=3, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    domain: str = Field(min_length=2, max_length=32)
    text: str = Field(min_length=1, max_length=20_000)


class KnowledgeSource(BaseModel):
    id: str
    title: str
    domain: str
    text: str
    document_id: str | None = None
    score: float
    retrieval: str
    chunk_count: int = 1


class KnowledgeResponse(BaseModel):
    question: str
    answer: str
    sources: list[KnowledgeSource]
    caveat: str


class KnowledgeIngestResponse(BaseModel):
    id: str
    title: str
    domain: str
    chunks_created: int
    status: str
