from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from deerflow.agents.middlewares.rag_selection_middleware import RAGSelectionMiddleware


def test_rag_selection_middleware_injects_selected_resource_ids() -> None:
    middleware = RAGSelectionMiddleware()
    state = {"messages": [HumanMessage(content="Answer from the selected KB.")]}
    runtime = SimpleNamespace(context={"rag_resource_ids": ["kb-1", "kb-2"]})

    result = middleware.before_agent(state=state, runtime=runtime)

    assert result is not None
    updated = result["messages"][-1]
    assert "selected_knowledge_bases" in updated.content
    assert "- kb-1" in updated.content
    assert "- kb-2" in updated.content
    assert "Knowledge-base-only mode is active" in updated.content
    assert "Answer from the selected KB." in updated.content


def test_rag_selection_middleware_noop_without_selection() -> None:
    middleware = RAGSelectionMiddleware()
    state = {"messages": [HumanMessage(content="Hello")]}
    runtime = SimpleNamespace(context={})

    result = middleware.before_agent(state=state, runtime=runtime)

    assert result is None
