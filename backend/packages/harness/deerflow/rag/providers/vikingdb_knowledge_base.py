"""VikingDB knowledge-base provider implementation for DeerFlow 2.x."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from deerflow.config.rag_config import VikingDBKnowledgeBaseConfig
from deerflow.rag.base import RAGProvider, RAGProviderError
from deerflow.rag.types import RAGChunk, RAGResource


class VikingDBKnowledgeBaseProvider(RAGProvider):
    """Volcengine VikingDB knowledge-base provider using signed HTTP requests."""

    provider_name = "vikingdb_knowledge_base"

    def __init__(self, config: VikingDBKnowledgeBaseConfig) -> None:
        self._config = config
        if not config.api_url:
            raise RAGProviderError("rag.vikingdb_knowledge_base.api_url is required when rag.provider=vikingdb_knowledge_base")
        if not config.api_ak:
            raise RAGProviderError("rag.vikingdb_knowledge_base.api_ak is required when rag.provider=vikingdb_knowledge_base")
        if not config.api_sk:
            raise RAGProviderError("rag.vikingdb_knowledge_base.api_sk is required when rag.provider=vikingdb_knowledge_base")

        self._base_url = _normalize_base_url(config.api_url)
        parsed = urlparse(self._base_url)
        self._host = parsed.netloc

    def _hmac_sha256(self, key: bytes, content: str) -> bytes:
        return hmac.new(key, content.encode("utf-8"), hashlib.sha256).digest()

    def _hash_sha256(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    def _get_signed_key(self, date: str) -> bytes:
        k_date = self._hmac_sha256(self._config.api_sk.encode("utf-8"), date)
        k_region = self._hmac_sha256(k_date, self._config.region)
        k_service = self._hmac_sha256(k_region, self._config.service)
        return self._hmac_sha256(k_service, "request")

    def _create_canonical_request(
        self,
        method: str,
        path: str,
        query_params: dict[str, Any],
        headers: dict[str, str],
        payload: bytes,
    ) -> tuple[str, str]:
        canonical_query_string = ""
        if query_params:
            encoded_params: list[str] = []
            for key in sorted(query_params.keys()):
                encoded_key = quote(str(key), safe="")
                encoded_value = quote(str(query_params[key]), safe="")
                encoded_params.append(f"{encoded_key}={encoded_value}")
            canonical_query_string = "&".join(encoded_params)

        canonical_headers_list: list[str] = []
        signed_headers_list: list[str] = []
        for header_name in sorted(headers.keys(), key=str.lower):
            header_name_lower = header_name.lower()
            canonical_headers_list.append(f"{header_name_lower}:{str(headers[header_name]).strip()}")
            signed_headers_list.append(header_name_lower)

        canonical_headers = "\n".join(canonical_headers_list) + "\n"
        signed_headers = ";".join(signed_headers_list)
        payload_hash = self._hash_sha256(payload).hex()
        canonical_request = "\n".join(
            [
                method.upper(),
                path or "/",
                canonical_query_string,
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )
        return canonical_request, signed_headers

    def _create_signed_headers(self, method: str, path: str, query_params: dict[str, Any], payload: bytes) -> dict[str, str]:
        now = datetime.utcnow()
        date_stamp = now.strftime("%Y%m%dT%H%M%SZ")
        auth_date = date_stamp[:8]
        headers = {
            "Content-Type": "application/json",
            "Host": self._host,
            "X-Content-Sha256": self._hash_sha256(payload).hex(),
            "X-Date": date_stamp,
        }

        canonical_request, signed_headers = self._create_canonical_request(
            method,
            path,
            query_params,
            headers,
            payload,
        )
        credential_scope = f"{auth_date}/{self._config.region}/{self._config.service}/request"
        string_to_sign = "\n".join(
            [
                "HMAC-SHA256",
                date_stamp,
                credential_scope,
                self._hash_sha256(canonical_request.encode("utf-8")).hex(),
            ]
        )
        signing_key = self._get_signed_key(auth_date)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        headers["Authorization"] = (
            f"HMAC-SHA256 Credential={self._config.api_ak}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return headers

    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
        query_params = params or {}
        payload = json.dumps(data).encode("utf-8") if data is not None else b""
        headers = self._create_signed_headers(method, path, query_params, payload)

        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._config.timeout_seconds) as client:
            response = await client.request(
                method,
                path,
                headers=headers,
                params=query_params or None,
                content=payload if payload else None,
            )

        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise RAGProviderError(f"Unexpected VikingDB response type for {path}: {type(body).__name__}")
        if body.get("code") not in (0, None):
            raise RAGProviderError(body.get("message") or f"VikingDB request failed for {path}")
        return body

    async def health(self) -> dict:
        payload = await self._request("POST", "/api/knowledge/collection/list")
        collection_list = self._extract_collection_list(payload.get("data"))
        return {
            "ok": True,
            "provider": self.provider_name,
            "api_url": self._base_url,
            "resource_count_hint": len(collection_list),
        }

    async def list_resources(self, query: str | None = None) -> list[RAGResource]:
        payload = await self._request("POST", "/api/knowledge/collection/list")
        resources: list[RAGResource] = []
        for item in self._extract_collection_list(payload.get("data")):
            resource_id = str(item.get("resource_id") or "").strip()
            collection_name = str(item.get("collection_name") or "").strip()
            if not resource_id or not collection_name:
                continue
            if query and query.lower() not in collection_name.lower():
                continue
            resources.append(
                RAGResource(
                    id=resource_id,
                    title=collection_name,
                    provider=self.provider_name,
                    description=item.get("description") or None,
                    metadata={k: v for k, v in item.items() if k not in {"resource_id", "collection_name", "description"}},
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
        target_ids = resource_ids or self._config.resource_ids
        if not target_ids:
            raise RAGProviderError(
                "No resource_ids supplied for retrieval and rag.vikingdb_knowledge_base.resource_ids is empty"
            )

        limit = top_k or self._config.retrieval_size
        chunks: list[RAGChunk] = []
        for resource_id in target_ids:
            payload = await self._request(
                "POST",
                "/api/knowledge/collection/search_knowledge",
                data={
                    "resource_id": resource_id,
                    "query": query,
                    "limit": limit,
                    "dense_weight": 0.5,
                    "pre_processing": {
                        "need_instruction": True,
                        "rewrite": False,
                        "return_token_usage": True,
                    },
                    "post_processing": {
                        "rerank_switch": True,
                        "chunk_diffusion_count": 0,
                        "chunk_group": True,
                        "get_attachment_link": True,
                    },
                },
            )
            for item in self._extract_result_list(payload.get("data")):
                content = item.get("content")
                if not isinstance(content, str) or not content.strip():
                    continue
                doc_info = item.get("doc_info") if isinstance(item.get("doc_info"), dict) else {}
                chunks.append(
                    RAGChunk(
                        text=content,
                        provider=self.provider_name,
                        score=float(item["score"]) if isinstance(item.get("score"), (int, float)) else None,
                        source_id=str(doc_info.get("doc_id")) if doc_info.get("doc_id") is not None else resource_id,
                        source_title=_first_non_empty_str(doc_info, "doc_name") or f"resource:{resource_id}",
                        source_uri=_first_non_empty_str(item, "attachment_link", "doc_url"),
                        chunk_id=str(item.get("chunk_id")) if item.get("chunk_id") is not None else None,
                        metadata={"resource_id": resource_id, **item},
                    )
                )

        chunks.sort(key=lambda item: item.score if item.score is not None else float("-inf"), reverse=True)
        return chunks[:limit]

    @staticmethod
    def _extract_collection_list(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            collection_list = data.get("collection_list")
            if isinstance(collection_list, list):
                return [item for item in collection_list if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_result_list(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            result_list = data.get("result_list")
            if isinstance(result_list, list):
                return [item for item in result_list if isinstance(item, dict)]
        return []


def _normalize_base_url(api_url: str) -> str:
    trimmed = api_url.strip().rstrip("/")
    if trimmed.startswith("http://") or trimmed.startswith("https://"):
        return trimmed
    return f"https://{trimmed}"


def _first_non_empty_str(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None
