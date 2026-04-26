import asyncio
from unittest.mock import AsyncMock, patch

from deerflow.config.rag_config import VikingDBKnowledgeBaseConfig
from deerflow.rag.providers.vikingdb_knowledge_base import VikingDBKnowledgeBaseProvider


def _provider() -> VikingDBKnowledgeBaseProvider:
    return VikingDBKnowledgeBaseProvider(
        VikingDBKnowledgeBaseConfig(
            api_url="api-knowledgebase.mlp.cn-beijing.volces.com",
            api_ak="test-ak",
            api_sk="test-sk",
            resource_ids=["kb-1"],
        )
    )


def test_vikingdb_list_resources_returns_collections() -> None:
    provider = _provider()

    with patch.object(
        provider,
        "_request",
        AsyncMock(
            return_value={
                "code": 0,
                "data": {
                    "collection_list": [
                        {"resource_id": "kb-1", "collection_name": "Product Docs", "description": "Main KB"},
                        {"resource_id": "kb-2", "collection_name": "FAQ", "description": ""},
                    ]
                },
            }
        ),
    ):
        resources = asyncio.run(provider.list_resources())

    assert [resource.id for resource in resources] == ["kb-1", "kb-2"]
    assert resources[0].title == "Product Docs"


def test_vikingdb_retrieve_returns_normalized_chunks() -> None:
    provider = _provider()

    with patch.object(
        provider,
        "_request",
        AsyncMock(
            return_value={
                "code": 0,
                "data": {
                    "result_list": [
                        {
                            "content": "VikingDB can search private knowledge bases.",
                            "score": 0.91,
                            "chunk_id": "chunk-1",
                            "attachment_link": "kb://docs/1",
                            "doc_info": {
                                "doc_id": "doc-1",
                                "doc_name": "VikingDB Intro",
                            },
                        }
                    ]
                },
            }
        ),
    ):
        chunks = asyncio.run(provider.retrieve("What does VikingDB do?"))

    assert len(chunks) == 1
    assert chunks[0].provider == "vikingdb_knowledge_base"
    assert chunks[0].text == "VikingDB can search private knowledge bases."
    assert chunks[0].source_id == "doc-1"
    assert chunks[0].source_title == "VikingDB Intro"


def test_vikingdb_health_counts_resources() -> None:
    provider = _provider()

    with patch.object(
        provider,
        "_request",
        AsyncMock(
            return_value={
                "code": 0,
                "data": {
                    "collection_list": [
                        {"resource_id": "kb-1", "collection_name": "Product Docs"},
                        {"resource_id": "kb-2", "collection_name": "FAQ"},
                    ]
                },
            }
        ),
    ):
        metadata = asyncio.run(provider.health())

    assert metadata["ok"] is True
    assert metadata["provider"] == "vikingdb_knowledge_base"
    assert metadata["resource_count_hint"] == 2
