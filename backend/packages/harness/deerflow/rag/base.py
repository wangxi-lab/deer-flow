"""Abstract interfaces for RAG providers."""

from __future__ import annotations

import abc
from pathlib import Path

from deerflow.rag.types import RAGChunk, RAGResource


class RAGProviderError(RuntimeError):
    """Raised when a provider request fails or the provider is misconfigured."""


class RAGProvider(abc.ABC):
    """Abstract base class for external RAG providers."""

    provider_name: str = "unknown"

    @abc.abstractmethod
    async def health(self) -> dict:
        """Return provider health metadata."""

    @abc.abstractmethod
    async def list_resources(self, query: str | None = None) -> list[RAGResource]:
        """List searchable resources."""

    @abc.abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        resource_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RAGChunk]:
        """Retrieve chunks relevant to a query."""

    async def upload_file(
        self,
        path: str | Path,
        *,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> RAGResource:
        """Upload a file to the backing knowledge base."""
        raise NotImplementedError(f"{self.provider_name} does not implement upload_file")
