"""RAGFlow provider implementation for DeerFlow 2.x."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from deerflow.config.rag_config import RAGFlowConfig
from deerflow.rag.base import RAGProvider, RAGProviderError
from deerflow.rag.types import RAGChunk, RAGResource


class RAGFlowProvider(RAGProvider):
    """RAGFlow-backed provider using the official HTTP API."""

    provider_name = "ragflow"

    def __init__(self, config: RAGFlowConfig) -> None:
        self._config = config
        if not config.api_url:
            raise RAGProviderError("rag.ragflow.api_url is required when rag.provider=ragflow")
        if not config.api_key:
            raise RAGProviderError("rag.ragflow.api_key is required when rag.provider=ragflow")
        self._base_url = config.api_url.rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._config.api_key}"}

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        timeout = kwargs.pop("timeout", self._config.timeout_seconds)
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=timeout) as client:
            response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code", 0) not in (0, None):
            raise RAGProviderError(payload.get("message") or f"RAGFlow request failed for {path}")
        if not isinstance(payload, dict):
            raise RAGProviderError(f"Unexpected RAGFlow response type for {path}: {type(payload).__name__}")
        return payload

    async def health(self) -> dict:
        payload = await self._request("GET", "/api/v1/datasets", params={"page": 1, "page_size": 1})
        return {
            "ok": True,
            "provider": self.provider_name,
            "api_url": self._base_url,
            "dataset_count_hint": len(self._extract_items(payload.get("data"))),
        }

    async def list_resources(self, query: str | None = None) -> list[RAGResource]:
        params: dict[str, Any] = {
            "page": 1,
            "page_size": self._config.page_size,
        }
        if query:
            params["name"] = query

        payload = await self._request("GET", "/api/v1/datasets", params=params)
        items = self._extract_items(payload.get("data"))
        resources: list[RAGResource] = []
        for item in items:
            resource_id = str(item.get("id") or item.get("dataset_id") or "")
            if not resource_id:
                continue
            resources.append(
                RAGResource(
                    id=resource_id,
                    title=str(item.get("name") or item.get("title") or resource_id),
                    provider=self.provider_name,
                    description=item.get("description"),
                    metadata={
                        k: v
                        for k, v in item.items()
                        if k not in {"id", "dataset_id", "name", "title", "description"}
                    },
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
        dataset_ids = resource_ids or self._config.dataset_ids
        if not dataset_ids:
            raise RAGProviderError("No dataset_ids supplied for retrieval and rag.ragflow.dataset_ids is empty")

        body: dict[str, Any] = {
            "question": query,
            "dataset_ids": dataset_ids,
            "page": 1,
            "page_size": max(top_k or self._config.retrieval_size, self._config.retrieval_size),
            "top_k": top_k or self._config.retrieval_size,
            "highlight": True,
        }
        if self._config.cross_languages:
            body["cross_languages"] = self._config.cross_languages

        payload = await self._request("POST", "/api/v1/retrieval", json=body)
        items = self._extract_items(payload.get("data"))
        chunks: list[RAGChunk] = []
        for item in items:
            text = item.get("content") or item.get("text") or item.get("chunk") or ""
            if not text:
                continue
            score = item.get("similarity")
            if score is None:
                score = item.get("score")
            chunks.append(
                RAGChunk(
                    text=str(text),
                    provider=self.provider_name,
                    score=float(score) if isinstance(score, (int, float)) else None,
                    source_id=_first_str(item, "dataset_id", "document_id", "doc_id"),
                    source_title=_first_str(item, "document_name", "title", "name"),
                    source_uri=_first_str(item, "docnm_kwd", "uri"),
                    chunk_id=_first_str(item, "chunk_id", "id"),
                    metadata=item,
                )
            )
        return chunks

    async def upload_file(
        self,
        path: str | Path,
        *,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> RAGResource:
        dataset_id = resource_id or (self._config.dataset_ids[0] if self._config.dataset_ids else None)
        if not dataset_id:
            raise RAGProviderError("upload_file requires a dataset id or rag.ragflow.dataset_ids[0]")

        file_path = Path(path)
        files = [("file", (file_path.name, file_path.read_bytes(), "application/octet-stream"))]
        payload = await self._request("POST", f"/api/v1/datasets/{dataset_id}/documents", files=files)
        items = self._extract_items(payload.get("data"))
        first = items[0] if items else {}
        doc_id = str(first.get("id") or first.get("document_id") or file_path.name)
        return RAGResource(
            id=doc_id,
            title=str(first.get("name") or file_path.name),
            provider=self.provider_name,
            description=None,
            metadata={"dataset_id": dataset_id, **(metadata or {}), **first},
        )

    @staticmethod
    def _extract_items(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            for key in ("docs", "datasets", "items", "records"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []


def _first_str(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None
