"""MCP server exposing the configured VikingDB knowledge-base provider."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from deerflow.config.app_config import get_app_config
from deerflow.config.rag_config import get_rag_config
from deerflow.rag.base import RAGProvider, RAGProviderError
from deerflow.rag.builder import get_rag_provider
from deerflow.rag.types import RAGChunk, RAGResource

PROVIDER_NAME = "vikingdb_knowledge_base"

mcp = FastMCP("vikingdb-knowledge-base")


def _serialize_chunk(chunk: RAGChunk) -> dict[str, Any]:
    """Return a JSON-safe chunk payload for MCP clients."""
    return chunk.model_dump(mode="json")


def _serialize_resource(resource: RAGResource) -> dict[str, Any]:
    """Return a JSON-safe resource payload for MCP clients."""
    return resource.model_dump(mode="json")


def _error_payload(message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "provider": PROVIDER_NAME,
        "error": message,
    }
    payload.update(extra)
    return payload


def _load_vikingdb_provider() -> RAGProvider:
    """Load app config and return the configured VikingDB RAG provider."""
    get_app_config()
    config = get_rag_config()
    if not config.enabled:
        raise RAGProviderError("RAG is disabled. Set rag.enabled=true in config.yaml before using the VikingDB MCP server.")
    if config.provider != PROVIDER_NAME:
        raise RAGProviderError(f"VikingDB MCP server requires rag.provider={PROVIDER_NAME!r}, current provider is {config.provider!r}.")

    provider = get_rag_provider()
    if provider is None:
        raise RAGProviderError("No RAG provider is available. Check rag.enabled and rag.provider in config.yaml.")
    if getattr(provider, "provider_name", None) != PROVIDER_NAME:
        raise RAGProviderError(f"Configured provider resolved to {getattr(provider, 'provider_name', type(provider).__name__)!r}, expected {PROVIDER_NAME!r}.")
    return provider


@mcp.tool()
async def search_knowledge(query: str, resource_ids: list[str] | None = None, top_k: int | None = None) -> dict[str, Any]:
    """Search VikingDB knowledge-base chunks for the user's question."""
    normalized_query = query.strip() if isinstance(query, str) else ""
    if not normalized_query:
        return _error_payload("query is required for VikingDB knowledge-base retrieval.", chunks=[])

    try:
        provider = _load_vikingdb_provider()
        chunks = await provider.retrieve(normalized_query, resource_ids=resource_ids, top_k=top_k)
        return {
            "ok": True,
            "provider": PROVIDER_NAME,
            "query": normalized_query,
            "resource_ids": resource_ids,
            "top_k": top_k,
            "chunks": [_serialize_chunk(chunk) for chunk in chunks],
        }
    except Exception as exc:
        return _error_payload(str(exc), chunks=[])


@mcp.tool()
async def list_resources(query: str | None = None) -> dict[str, Any]:
    """List configured VikingDB knowledge-base resources."""
    try:
        provider = _load_vikingdb_provider()
        resources = await provider.list_resources(query=query)
        return {
            "ok": True,
            "provider": PROVIDER_NAME,
            "query": query,
            "resources": [_serialize_resource(resource) for resource in resources],
        }
    except Exception as exc:
        return _error_payload(str(exc), resources=[])


@mcp.tool()
async def health() -> dict[str, Any]:
    """Check whether the configured VikingDB knowledge-base provider is reachable."""
    try:
        provider = _load_vikingdb_provider()
        payload = await provider.health()
        return {
            "ok": bool(payload.get("ok", True)),
            "provider": PROVIDER_NAME,
            **payload,
        }
    except Exception as exc:
        return _error_payload(str(exc))


if __name__ == "__main__":
    mcp.run(transport="stdio")
