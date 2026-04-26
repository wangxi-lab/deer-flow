import asyncio
from unittest.mock import AsyncMock, patch

from deerflow.config.rag_config import QdrantConfig
from deerflow.rag.providers.qdrant import QdrantProvider


def _provider() -> QdrantProvider:
    with patch("deerflow.rag.providers.qdrant.OpenAIEmbeddings") as mock_embeddings:
        mock_embeddings.return_value.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        return QdrantProvider(
            QdrantConfig(
                url="http://localhost:6333",
                collection_names=["docs"],
                embedding={"model": "text-embedding-3-small", "api_key": "secret"},
            )
        )


def test_qdrant_list_resources_returns_collections() -> None:
    provider = _provider()

    with patch.object(
        provider,
        "_request",
        AsyncMock(return_value={"status": "ok", "result": {"collections": [{"name": "docs"}, {"name": "faq"}]}}),
    ):
        resources = asyncio.run(provider.list_resources())

    assert [resource.id for resource in resources] == ["docs", "faq"]


def test_qdrant_retrieve_returns_normalized_chunks() -> None:
    provider = _provider()

    with patch.object(
        provider,
        "_request",
        AsyncMock(
            return_value={
                "status": "ok",
                "result": {
                    "points": [
                        {
                            "id": 123,
                            "score": 0.92,
                            "payload": {
                                "text": "DeerFlow supports thread-local uploads.",
                                "title": "Product FAQ",
                                "source": "kb://faq",
                            },
                        }
                    ]
                },
            }
        ),
    ):
        chunks = asyncio.run(provider.retrieve("what can DeerFlow do?"))

    assert len(chunks) == 1
    assert chunks[0].provider == "qdrant"
    assert chunks[0].text == "DeerFlow supports thread-local uploads."
    assert chunks[0].source_id == "docs"
    assert chunks[0].source_title == "Product FAQ"
