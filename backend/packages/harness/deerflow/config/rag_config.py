"""Configuration models for external RAG providers."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RAGFlowConfig(BaseModel):
    """Configuration for the RAGFlow provider."""

    api_url: str | None = Field(default=None, description="Base URL of the RAGFlow API service")
    api_key: str | None = Field(default=None, description="Bearer token for the RAGFlow API")
    dataset_ids: list[str] = Field(default_factory=list, description="Default dataset ids to search when none are specified")
    timeout_seconds: float = Field(default=30.0, description="HTTP timeout in seconds for RAGFlow API calls")
    retrieval_size: int = Field(default=5, ge=1, le=100, description="Default number of chunks to retrieve")
    page_size: int = Field(default=30, ge=1, le=100, description="Page size used when listing datasets")
    cross_languages: list[str] = Field(default_factory=list, description="Optional cross-language retrieval hints")


class OpenAIEmbeddingConfig(BaseModel):
    """Configuration for an OpenAI-compatible embedding endpoint."""

    model: str | None = Field(default=None, description="Embedding model name")
    api_key: str | None = Field(default=None, description="API key for the embedding provider")
    base_url: str | None = Field(default=None, description="Optional OpenAI-compatible base URL")


class QdrantConfig(BaseModel):
    """Configuration for the Qdrant provider."""

    url: str | None = Field(default=None, description="Base URL of the Qdrant HTTP API")
    api_key: str | None = Field(default=None, description="Optional Qdrant API key")
    collection_names: list[str] = Field(default_factory=list, description="Default collection names to search when none are specified")
    timeout_seconds: float = Field(default=30.0, description="HTTP timeout in seconds for Qdrant API calls")
    retrieval_size: int = Field(default=5, ge=1, le=100, description="Default number of chunks to retrieve")
    score_threshold: float | None = Field(default=None, description="Optional minimum score threshold")
    vector_name: str | None = Field(default=None, description="Optional named vector to query")
    text_payload_key: str = Field(default="text", description="Payload key containing chunk text")
    title_payload_key: str = Field(default="title", description="Payload key containing source title")
    uri_payload_key: str = Field(default="source", description="Payload key containing source URI")
    embedding: OpenAIEmbeddingConfig = Field(default_factory=OpenAIEmbeddingConfig, description="Embedding model configuration")

    @model_validator(mode="after")
    def _normalize_collections(self) -> "QdrantConfig":
        self.collection_names = [name for name in self.collection_names if isinstance(name, str) and name.strip()]
        return self


class VikingDBKnowledgeBaseConfig(BaseModel):
    """Configuration for the VikingDB knowledge-base provider."""

    api_url: str | None = Field(default=None, description="VikingDB knowledge-base API host or base URL")
    api_ak: str | None = Field(default=None, description="Volcengine access key for request signing")
    api_sk: str | None = Field(default=None, description="Volcengine secret key for request signing")
    resource_ids: list[str] = Field(default_factory=list, description="Default knowledge-base resource ids to search when none are specified")
    timeout_seconds: float = Field(default=30.0, description="HTTP timeout in seconds for VikingDB API calls")
    retrieval_size: int = Field(default=5, ge=1, le=100, description="Default number of chunks to retrieve")
    region: str = Field(default="cn-north-1", description="Volcengine signing region")
    service: str = Field(default="air", description="Volcengine signing service name")

    @model_validator(mode="after")
    def _normalize_resources(self) -> "VikingDBKnowledgeBaseConfig":
        self.resource_ids = [item for item in self.resource_ids if isinstance(item, str) and item.strip()]
        return self


class RAGConfig(BaseModel):
    """Top-level RAG configuration."""

    enabled: bool = Field(default=False, description="Whether external RAG integration is enabled")
    provider: str | None = Field(default=None, description="Name of the configured RAG provider")
    ragflow: RAGFlowConfig = Field(default_factory=RAGFlowConfig, description="RAGFlow provider settings")
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig, description="Qdrant provider settings")
    vikingdb_knowledge_base: VikingDBKnowledgeBaseConfig = Field(
        default_factory=VikingDBKnowledgeBaseConfig,
        description="VikingDB knowledge-base provider settings",
    )


_rag_config: RAGConfig | None = None


def get_rag_config() -> RAGConfig:
    """Return the current RAG configuration singleton."""
    global _rag_config
    if _rag_config is None:
        _rag_config = RAGConfig()
    return _rag_config


def load_rag_config_from_dict(data: dict) -> RAGConfig:
    """Load the RAG config from a config.yaml section."""
    global _rag_config
    _rag_config = RAGConfig.model_validate(data)
    return _rag_config
