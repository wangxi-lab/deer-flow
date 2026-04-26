"""Built-in knowledge-base search tool backed by the configured RAG provider."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain.tools import ToolRuntime, tool
from langgraph.typing import ContextT

from deerflow.agents.thread_state import ThreadState

from deerflow.rag import RAGProviderError, get_rag_provider


def _get_runtime_resource_ids(
    runtime: ToolRuntime[ContextT, ThreadState] | None,
) -> list[str] | None:
    if runtime is None:
        return None

    if runtime.context:
        value = runtime.context.get("rag_resource_ids")
        normalized = _normalize_resource_ids(value)
        if normalized:
            return normalized

    config = getattr(runtime, "config", None) or {}
    configurable = config.get("configurable", {})
    normalized = _normalize_resource_ids(configurable.get("rag_resource_ids"))
    if normalized:
        return normalized

    return None


def _normalize_resource_ids(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    normalized = [item for item in value if isinstance(item, str) and item.strip()]
    return normalized or None


@tool("local_search", parse_docstring=True)
def local_search_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    query: str,
    resource_ids: list[str] | None = None,
    top_k: int | None = None,
) -> list[dict] | str:
    """Search the configured external knowledge base for relevant chunks.

    Use this tool when the user asks about a private knowledge base, company docs,
    or an external RAG-connected corpus rather than only the files uploaded in the
    current thread.

    Args:
        query: Natural-language search query.
        resource_ids: Optional list of provider resource ids to limit retrieval. If omitted, thread-selected resource ids are used.
        top_k: Optional max number of chunks to return.
    """
    provider = get_rag_provider()
    if provider is None:
        return "External RAG is not enabled in config.yaml."

    async def _run() -> list[dict]:
        effective_resource_ids = resource_ids or _get_runtime_resource_ids(runtime)
        chunks = await provider.retrieve(
            query,
            resource_ids=effective_resource_ids,
            top_k=top_k,
        )
        return [chunk.model_dump() for chunk in chunks]

    try:
        return asyncio.run(_run())
    except RAGProviderError as exc:
        return f"RAG provider error: {exc}"
