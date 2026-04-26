from __future__ import annotations

from types import SimpleNamespace

import pytest

from deerflow.mcp_servers import vikingdb_knowledge_base as server
from deerflow.rag.types import RAGChunk, RAGResource


class FakeProvider:
    provider_name = "vikingdb_knowledge_base"

    def __init__(self) -> None:
        self.retrieve_calls: list[dict] = []
        self.list_resource_queries: list[str | None] = []

    async def health(self) -> dict:
        return {"ok": True, "provider": self.provider_name, "resource_count_hint": 1}

    async def list_resources(self, query: str | None = None) -> list[RAGResource]:
        self.list_resource_queries.append(query)
        return [
            RAGResource(
                id="kb-1",
                title="Internal Handbook",
                provider=self.provider_name,
                description="Private docs",
                metadata={"owner": "team-a"},
            )
        ]

    async def retrieve(
        self,
        query: str,
        *,
        resource_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RAGChunk]:
        self.retrieve_calls.append({"query": query, "resource_ids": resource_ids, "top_k": top_k})
        return [
            RAGChunk(
                text="DeerFlow can retrieve from VikingDB.",
                provider=self.provider_name,
                score=0.91,
                source_id="doc-1",
                source_title="VikingDB Guide",
                source_uri="https://example.com/vikingdb-guide",
                chunk_id="chunk-1",
                metadata={"resource_id": "kb-1"},
            )
        ]


def _patch_provider(monkeypatch: pytest.MonkeyPatch, provider: FakeProvider, *, enabled: bool = True, provider_name: str | None = None) -> None:
    monkeypatch.setattr(server, "get_app_config", lambda: object())
    monkeypatch.setattr(
        server,
        "get_rag_config",
        lambda: SimpleNamespace(enabled=enabled, provider=provider_name or server.PROVIDER_NAME),
    )
    monkeypatch.setattr(server, "get_rag_provider", lambda: provider)


@pytest.mark.anyio
async def test_search_knowledge_serializes_chunks_and_forwards_options(monkeypatch: pytest.MonkeyPatch):
    provider = FakeProvider()
    _patch_provider(monkeypatch, provider)

    result = await server.search_knowledge("  how does RAG work?  ", resource_ids=["kb-1"], top_k=3)

    assert result["ok"] is True
    assert provider.retrieve_calls == [{"query": "how does RAG work?", "resource_ids": ["kb-1"], "top_k": 3}]
    assert result["chunks"] == [
        {
            "text": "DeerFlow can retrieve from VikingDB.",
            "provider": "vikingdb_knowledge_base",
            "score": 0.91,
            "source_id": "doc-1",
            "source_title": "VikingDB Guide",
            "source_uri": "https://example.com/vikingdb-guide",
            "chunk_id": "chunk-1",
            "metadata": {"resource_id": "kb-1"},
        }
    ]


@pytest.mark.anyio
async def test_list_resources_serializes_resources_and_forwards_query(monkeypatch: pytest.MonkeyPatch):
    provider = FakeProvider()
    _patch_provider(monkeypatch, provider)

    result = await server.list_resources(query="handbook")

    assert result["ok"] is True
    assert provider.list_resource_queries == ["handbook"]
    assert result["resources"] == [
        {
            "id": "kb-1",
            "title": "Internal Handbook",
            "provider": "vikingdb_knowledge_base",
            "description": "Private docs",
            "metadata": {"owner": "team-a"},
        }
    ]


@pytest.mark.anyio
async def test_health_returns_provider_payload(monkeypatch: pytest.MonkeyPatch):
    provider = FakeProvider()
    _patch_provider(monkeypatch, provider)

    result = await server.health()

    assert result == {"ok": True, "provider": "vikingdb_knowledge_base", "resource_count_hint": 1}


@pytest.mark.anyio
async def test_provider_misconfiguration_returns_clear_error(monkeypatch: pytest.MonkeyPatch):
    provider = FakeProvider()
    _patch_provider(monkeypatch, provider, provider_name="ragflow")

    result = await server.search_knowledge("question")

    assert result["ok"] is False
    assert result["chunks"] == []
    assert "requires rag.provider='vikingdb_knowledge_base'" in result["error"]


@pytest.mark.anyio
async def test_disabled_rag_returns_clear_error(monkeypatch: pytest.MonkeyPatch):
    provider = FakeProvider()
    _patch_provider(monkeypatch, provider, enabled=False)

    result = await server.list_resources()

    assert result["ok"] is False
    assert result["resources"] == []
    assert "RAG is disabled" in result["error"]
