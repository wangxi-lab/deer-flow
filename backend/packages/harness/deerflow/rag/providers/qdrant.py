"""Qdrant provider implementation for DeerFlow 2.x."""

from __future__ import annotations

from typing import Any

import httpx
from langchain_openai import OpenAIEmbeddings

from deerflow.config.rag_config import QdrantConfig
from deerflow.rag.base import RAGProvider, RAGProviderError
from deerflow.rag.types import RAGChunk, RAGResource


class QdrantProvider(RAGProvider):
    """Qdrant-backed provider using the official HTTP API."""

    provider_name = "qdrant"

    def __init__(self, config: QdrantConfig) -> None:
        self._config = config
        if not config.url:
            raise RAGProviderError("rag.qdrant.url is required when rag.provider=qdrant")
        if not config.embedding.model:
            raise RAGProviderError("rag.qdrant.embedding.model is required when rag.provider=qdrant")
        if not config.embedding.api_key:
            raise RAGProviderError("rag.qdrant.embedding.api_key is required when rag.provider=qdrant")

        self._base_url = config.url.rstrip("/")
        embedding_kwargs: dict[str, Any] = {
            "model": config.embedding.model,
            "api_key": config.embedding.api_key,
        }
        if config.embedding.base_url:
            embedding_kwargs["base_url"] = config.embedding.base_url
        self._embeddings = OpenAIEmbeddings(**embedding_kwargs)

    @property
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._config.api_key:
            headers["api-key"] = self._config.api_key
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        timeout = kwargs.pop("timeout", self._config.timeout_seconds)
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=timeout) as client:
            response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RAGProviderError(f"Unexpected Qdrant response type for {path}: {type(payload).__name__}")
        status = payload.get("status")
        if isinstance(status, str) and status.lower() not in {"ok", "green", "healthy"}:
            raise RAGProviderError(payload.get("message") or f"Qdrant request failed for {path}")
        return payload

    async def _embed_query(self, query: str) -> list[float]:
        return await self._embeddings.aembed_query(query)

    async def health(self) -> dict:
        payload = await self._request("GET", "/collections")
        collections = self._extract_collections(payload.get("result"))
        return {
            "ok": True,
            "provider": self.provider_name,
            "url": self._base_url,
            "collection_count_hint": len(collections),
        }

    async def list_resources(self, query: str | None = None) -> list[RAGResource]:
        payload = await self._request("GET", "/collections")
        resources: list[RAGResource] = []
        for item in self._extract_collections(payload.get("result")):
            collection_name = str(item.get("name") or "").strip()
            if not collection_name:
                continue
            if query and query.lower() not in collection_name.lower():
                continue
            resources.append(
                RAGResource(
                    id=collection_name,
                    title=collection_name,
                    provider=self.provider_name,
                    metadata={k: v for k, v in item.items() if k != "name"},
                )
            )
        return resources

    async def retrieve(
        self,
        query: str,
        *,
        resource_ids: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RAGChunk]:
        collection_names = resource_ids or self._config.collection_names
        if not collection_names:
            raise RAGProviderError("No collection_names supplied for retrieval and rag.qdrant.collection_names is empty")

        vector = await self._embed_query(query)
        limit = top_k or self._config.retrieval_size
        chunks: list[RAGChunk] = []
        for collection_name in collection_names:
            body: dict[str, Any] = {
                "query": vector,
                "limit": limit,
                "with_payload": True,
                "with_vector": False,
            }
            if self._config.vector_name:
                body["using"] = self._config.vector_name
            if self._config.score_threshold is not None:
                body["score_threshold"] = self._config.score_threshold

            payload = await self._request("POST", f"/collections/{collection_name}/points/query", json=body)
            points = self._extract_points(payload.get("result"))
            for point in points:
                payload_data = point.get("payload")
                if not isinstance(payload_data, dict):
                    continue
                text = _string_from_payload(payload_data, self._config.text_payload_key)
                if not text:
                    continue
                score = point.get("score")
                chunks.append(
                    RAGChunk(
                        text=text,
                        provider=self.provider_name,
                        score=float(score) if isinstance(score, (int, float)) else None,
                        source_id=collection_name,
                        source_title=_string_from_payload(payload_data, self._config.title_payload_key) or collection_name,
                        source_uri=_string_from_payload(payload_data, self._config.uri_payload_key),
                        chunk_id=str(point.get("id")) if point.get("id") is not None else None,
                        metadata={"collection_name": collection_name, **point},
                    )
                )

        chunks.sort(key=lambda item: item.score if item.score is not None else float("-inf"), reverse=True)
        return chunks[:limit]

    @staticmethod
    def _extract_collections(result: Any) -> list[dict[str, Any]]:
        if isinstance(result, dict):
            collections = result.get("collections")
            if isinstance(collections, list):
                return [item for item in collections if isinstance(item, dict)]
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_points(result: Any) -> list[dict[str, Any]]:
        if isinstance(result, dict):
            points = result.get("points")
            if isinstance(points, list):
                return [item for item in points if isinstance(item, dict)]
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        return []


def _string_from_payload(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, list):
        parts = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if parts:
            return "\n".join(parts)
    return None
