"""RAG API router for external knowledge-base providers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from deerflow.config.rag_config import get_rag_config
from deerflow.rag import RAGProviderError, get_rag_provider

router = APIRouter(prefix="/api/rag", tags=["rag"])


class RAGConfigResponse(BaseModel):
    """Response model for RAG configuration."""

    enabled: bool = Field(..., description="Whether external RAG is enabled")
    provider: str | None = Field(default=None, description="Configured RAG provider")
    default_resource_ids: list[str] = Field(default_factory=list, description="Default resource ids used for retrieval")


class RAGHealthResponse(BaseModel):
    """Response model for RAG health checks."""

    enabled: bool = Field(..., description="Whether external RAG is enabled")
    provider: str | None = Field(default=None, description="Configured RAG provider")
    ok: bool = Field(..., description="Whether the provider health check passed")
    detail: str | None = Field(default=None, description="Optional diagnostic message")
    metadata: dict = Field(default_factory=dict, description="Provider-specific health metadata")


class RAGResourceResponse(BaseModel):
    """A knowledge-base resource exposed by the provider."""

    id: str
    title: str
    provider: str
    description: str | None = None
    metadata: dict = Field(default_factory=dict)


class RAGResourcesResponse(BaseModel):
    """Response model for listing resources."""

    resources: list[RAGResourceResponse] = Field(default_factory=list)


class RAGRetrieveRequest(BaseModel):
    """Request model for retrieval."""

    query: str = Field(..., min_length=1, description="Search query")
    resource_ids: list[str] | None = Field(default=None, description="Optional resource ids to constrain retrieval")
    top_k: int | None = Field(default=None, ge=1, le=100, description="Maximum number of chunks to return")


class RAGChunkResponse(BaseModel):
    """A normalized retrieved chunk."""

    text: str
    provider: str
    score: float | None = None
    source_id: str | None = None
    source_title: str | None = None
    source_uri: str | None = None
    chunk_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class RAGRetrieveResponse(BaseModel):
    """Response model for retrieval."""

    chunks: list[RAGChunkResponse] = Field(default_factory=list)


def _as_payload(item: object) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump()  # type: ignore[no-any-return, attr-defined]
    if isinstance(item, dict):
        return item
    raise TypeError(f"Unsupported RAG payload item type: {type(item).__name__}")


def _provider_or_503():
    provider = get_rag_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="External RAG is disabled or not configured.")
    return provider


def _default_resource_ids() -> list[str]:
    config = get_rag_config()
    if config.provider == "ragflow":
        return config.ragflow.dataset_ids
    if config.provider == "qdrant":
        return config.qdrant.collection_names
    if config.provider == "vikingdb_knowledge_base":
        return config.vikingdb_knowledge_base.resource_ids
    return []


@router.get("/config", response_model=RAGConfigResponse, summary="Get RAG Configuration")
async def get_rag_config_endpoint() -> RAGConfigResponse:
    """Return the current RAG configuration."""
    config = get_rag_config()
    return RAGConfigResponse(
        enabled=config.enabled,
        provider=config.provider,
        default_resource_ids=_default_resource_ids(),
    )


@router.get("/health", response_model=RAGHealthResponse, summary="Check RAG Provider Health")
async def get_rag_health() -> RAGHealthResponse:
    """Check the configured RAG provider."""
    config = get_rag_config()
    if not config.enabled or not config.provider:
        return RAGHealthResponse(enabled=False, provider=config.provider, ok=False, detail="External RAG is disabled.")

    try:
        provider = _provider_or_503()
        metadata = await provider.health()
    except (HTTPException, RAGProviderError) as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
        return RAGHealthResponse(enabled=True, provider=config.provider, ok=False, detail=detail)

    return RAGHealthResponse(enabled=True, provider=config.provider, ok=True, metadata=metadata)


@router.get("/resources", response_model=RAGResourcesResponse, summary="List RAG Resources")
async def list_rag_resources(query: str | None = None) -> RAGResourcesResponse:
    """List searchable knowledge-base resources."""
    try:
        provider = _provider_or_503()
        resources = await provider.list_resources(query=query)
    except HTTPException:
        raise
    except RAGProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return RAGResourcesResponse(resources=[RAGResourceResponse(**_as_payload(resource)) for resource in resources])


@router.post("/retrieve", response_model=RAGRetrieveResponse, summary="Retrieve RAG Chunks")
async def retrieve_rag_chunks(request: RAGRetrieveRequest) -> RAGRetrieveResponse:
    """Retrieve relevant chunks from the configured knowledge base."""
    try:
        provider = _provider_or_503()
        chunks = await provider.retrieve(
            request.query,
            resource_ids=request.resource_ids,
            top_k=request.top_k,
        )
    except HTTPException:
        raise
    except RAGProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return RAGRetrieveResponse(chunks=[RAGChunkResponse(**_as_payload(chunk)) for chunk in chunks])
