"""Shared models for external RAG providers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RAGResource(BaseModel):
    """A searchable knowledge-base resource."""

    id: str = Field(..., description="Stable provider-specific resource id")
    title: str = Field(..., description="Human-readable resource title")
    provider: str = Field(..., description="Provider name")
    description: str | None = Field(default=None, description="Optional resource description")
    metadata: dict = Field(default_factory=dict, description="Provider-specific metadata")


class RAGChunk(BaseModel):
    """A retrieved chunk returned from a provider."""

    text: str = Field(..., description="Chunk text")
    provider: str = Field(..., description="Provider name")
    score: float | None = Field(default=None, description="Optional relevance score")
    source_id: str | None = Field(default=None, description="Source resource id")
    source_title: str | None = Field(default=None, description="Source resource title")
    source_uri: str | None = Field(default=None, description="Optional source URI")
    chunk_id: str | None = Field(default=None, description="Provider-specific chunk id")
    metadata: dict = Field(default_factory=dict, description="Provider-specific metadata")
