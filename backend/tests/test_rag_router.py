from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import rag


def test_rag_config_endpoint_returns_current_settings() -> None:
    app = FastAPI()
    app.include_router(rag.router)

    with patch("app.gateway.routers.rag.get_rag_config") as mock_get_config:
        mock_get_config.return_value.enabled = True
        mock_get_config.return_value.provider = "ragflow"
        mock_get_config.return_value.ragflow.dataset_ids = ["ds-1", "ds-2"]
        with TestClient(app) as client:
            response = client.get("/api/rag/config")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "provider": "ragflow",
        "default_resource_ids": ["ds-1", "ds-2"],
    }


def test_rag_resources_endpoint_returns_provider_resources() -> None:
    app = FastAPI()
    app.include_router(rag.router)
    provider = AsyncMock()
    provider.list_resources.return_value = [
        {
            "id": "kb-1",
            "title": "Knowledge Base 1",
            "provider": "ragflow",
            "description": "Main docs",
            "metadata": {"owner": "team"},
        }
    ]

    with patch("app.gateway.routers.rag._provider_or_503", return_value=provider):
        with TestClient(app) as client:
            response = client.get("/api/rag/resources")

    assert response.status_code == 200
    assert response.json()["resources"][0]["id"] == "kb-1"


def test_rag_retrieve_endpoint_surfaces_provider_errors() -> None:
    app = FastAPI()
    app.include_router(rag.router)
    provider = AsyncMock()
    provider.retrieve.side_effect = rag.RAGProviderError("boom")

    with patch("app.gateway.routers.rag._provider_or_503", return_value=provider):
        with TestClient(app) as client:
            response = client.post("/api/rag/retrieve", json={"query": "hello"})

    assert response.status_code == 502
    assert response.json()["detail"] == "boom"


def test_rag_config_endpoint_returns_qdrant_defaults() -> None:
    app = FastAPI()
    app.include_router(rag.router)

    with patch("app.gateway.routers.rag.get_rag_config") as mock_get_config:
        mock_get_config.return_value.enabled = True
        mock_get_config.return_value.provider = "qdrant"
        mock_get_config.return_value.qdrant.collection_names = ["docs", "faq"]
        with TestClient(app) as client:
            response = client.get("/api/rag/config")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "provider": "qdrant",
        "default_resource_ids": ["docs", "faq"],
    }


def test_rag_config_endpoint_returns_vikingdb_defaults() -> None:
    app = FastAPI()
    app.include_router(rag.router)

    with patch("app.gateway.routers.rag.get_rag_config") as mock_get_config:
        mock_get_config.return_value.enabled = True
        mock_get_config.return_value.provider = "vikingdb_knowledge_base"
        mock_get_config.return_value.vikingdb_knowledge_base.resource_ids = ["kb-1", "kb-2"]
        with TestClient(app) as client:
            response = client.get("/api/rag/config")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "provider": "vikingdb_knowledge_base",
        "default_resource_ids": ["kb-1", "kb-2"],
    }
