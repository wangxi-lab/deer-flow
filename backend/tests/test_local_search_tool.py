from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from deerflow.tools.builtins.local_search_tool import local_search_tool


def test_local_search_tool_returns_disabled_message_when_provider_missing() -> None:
    with patch("deerflow.tools.builtins.local_search_tool.get_rag_provider", return_value=None):
        result = local_search_tool.func(
            runtime=SimpleNamespace(context={}, config={"configurable": {}}),
            query="what is deerflow",
        )

    assert result == "External RAG is not enabled in config.yaml."


def test_local_search_tool_returns_serialized_chunks() -> None:
    provider = AsyncMock()
    provider.retrieve.return_value = [
        type(
            "Chunk",
            (),
            {
                "model_dump": lambda self: {"text": "answer", "provider": "ragflow", "metadata": {}},
            },
        )()
    ]

    with patch("deerflow.tools.builtins.local_search_tool.get_rag_provider", return_value=provider):
        result = local_search_tool.func(
            runtime=SimpleNamespace(context={}, config={"configurable": {}}),
            query="what is deerflow",
        )

    assert result == [{"text": "answer", "provider": "ragflow", "metadata": {}}]


def test_local_search_tool_uses_thread_selected_resource_ids() -> None:
    provider = AsyncMock()
    provider.retrieve.return_value = []
    runtime = SimpleNamespace(
        context={"rag_resource_ids": ["kb-1", "kb-2"]},
        config={"configurable": {}},
    )

    with patch("deerflow.tools.builtins.local_search_tool.get_rag_provider", return_value=provider):
        local_search_tool.func(runtime=runtime, query="what is deerflow")

    provider.retrieve.assert_awaited_once_with(
        "what is deerflow",
        resource_ids=["kb-1", "kb-2"],
        top_k=None,
    )
