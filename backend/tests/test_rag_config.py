from deerflow.config.rag_config import RAGConfig, get_rag_config, load_rag_config_from_dict


def test_load_rag_config_from_dict_sets_defaults() -> None:
    config = load_rag_config_from_dict(
        {
            "enabled": True,
            "provider": "ragflow",
            "ragflow": {
                "api_url": "http://localhost:9380",
                "api_key": "secret",
                "dataset_ids": ["dataset-1"],
            },
        }
    )

    assert config.enabled is True
    assert config.provider == "ragflow"
    assert config.ragflow.dataset_ids == ["dataset-1"]
    assert get_rag_config() is config


def test_get_rag_config_returns_default_when_uninitialized() -> None:
    config = load_rag_config_from_dict({})
    assert isinstance(config, RAGConfig)
    assert config.enabled is False
    assert config.provider is None


def test_load_qdrant_rag_config_from_dict() -> None:
    config = load_rag_config_from_dict(
        {
            "enabled": True,
            "provider": "qdrant",
            "qdrant": {
                "url": "http://localhost:6333",
                "collection_names": ["docs"],
                "embedding": {
                    "model": "text-embedding-3-small",
                    "api_key": "secret",
                },
            },
        }
    )

    assert config.enabled is True
    assert config.provider == "qdrant"
    assert config.qdrant.collection_names == ["docs"]
    assert config.qdrant.embedding.model == "text-embedding-3-small"


def test_load_vikingdb_rag_config_from_dict() -> None:
    config = load_rag_config_from_dict(
        {
            "enabled": True,
            "provider": "vikingdb_knowledge_base",
            "vikingdb_knowledge_base": {
                "api_url": "api-knowledgebase.mlp.cn-beijing.volces.com",
                "api_ak": "test-ak",
                "api_sk": "test-sk",
                "resource_ids": ["kb-1"],
            },
        }
    )

    assert config.enabled is True
    assert config.provider == "vikingdb_knowledge_base"
    assert config.vikingdb_knowledge_base.resource_ids == ["kb-1"]
    assert config.vikingdb_knowledge_base.region == "cn-north-1"
