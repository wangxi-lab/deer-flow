"""Factory helpers for RAG providers."""

from __future__ import annotations

from deerflow.config.rag_config import get_rag_config
from deerflow.rag.base import RAGProvider, RAGProviderError
from deerflow.rag.providers.qdrant import QdrantProvider
from deerflow.rag.providers.ragflow import RAGFlowProvider
from deerflow.rag.providers.vikingdb_knowledge_base import VikingDBKnowledgeBaseProvider


def get_rag_provider() -> RAGProvider | None:
    """Build the configured RAG provider, if enabled."""
    config = get_rag_config()
    if not config.enabled or not config.provider:
        return None
    if config.provider == "ragflow":
        return RAGFlowProvider(config.ragflow)
    if config.provider == "qdrant":
        return QdrantProvider(config.qdrant)
    if config.provider == "vikingdb_knowledge_base":
        return VikingDBKnowledgeBaseProvider(config.vikingdb_knowledge_base)
    raise RAGProviderError(f"Unsupported RAG provider: {config.provider}")
