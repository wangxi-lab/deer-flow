from types import SimpleNamespace

import pytest
from langchain_core.messages import ToolMessage

from deerflow.agents.middlewares.knowledge_base_only_middleware import KnowledgeBaseOnlyMiddleware


class _ModelRequest:
    def __init__(self, tools: list[object], runtime: object | None = None):
        self.tools = tools
        self.runtime = runtime

    def override(self, **updates):
        return _ModelRequest(
            tools=updates.get("tools", self.tools),
            runtime=updates.get("runtime", self.runtime),
        )


def _runtime(resource_ids: list[str] | None = None):
    return SimpleNamespace(context={"rag_resource_ids": resource_ids or []}, config={})


def _tool(name: str):
    return SimpleNamespace(name=name)


def _tool_request(name: str, runtime: object | None = None, tool_call_id: str = "tc-1"):
    return SimpleNamespace(
        tool_call={"name": name, "id": tool_call_id},
        runtime=runtime,
    )


def test_wrap_model_call_filters_to_kb_only_tools_when_selection_exists():
    middleware = KnowledgeBaseOnlyMiddleware()
    request = _ModelRequest(
        tools=[_tool("web_search"), _tool("local_search"), _tool("ask_clarification"), _tool("read_file")],
        runtime=_runtime(["kb-1"]),
    )

    filtered_names: list[str] = []

    def handler(req):
        filtered_names.extend(tool.name for tool in req.tools)
        return "ok"

    result = middleware.wrap_model_call(request, handler)

    assert result == "ok"
    assert filtered_names == ["local_search", "ask_clarification"]


def test_wrap_model_call_noop_without_kb_selection():
    middleware = KnowledgeBaseOnlyMiddleware()
    request = _ModelRequest(
        tools=[_tool("web_search"), _tool("local_search")],
        runtime=_runtime([]),
    )

    seen_names: list[str] = []

    def handler(req):
        seen_names.extend(tool.name for tool in req.tools)
        return "ok"

    middleware.wrap_model_call(request, handler)

    assert seen_names == ["web_search", "local_search"]


def test_wrap_tool_call_blocks_non_kb_tool_when_selection_exists():
    middleware = KnowledgeBaseOnlyMiddleware()
    request = _tool_request("web_search", runtime=_runtime(["kb-1"]))

    result = middleware.wrap_tool_call(request, lambda _req: pytest.fail("handler should not be called"))

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert result.name == "web_search"
    assert "Knowledge-base-only mode is active" in result.text


def test_wrap_tool_call_allows_local_search_when_selection_exists():
    middleware = KnowledgeBaseOnlyMiddleware()
    request = _tool_request("local_search", runtime=_runtime(["kb-1"]))
    expected = ToolMessage(content="ok", tool_call_id="tc-1", name="local_search")

    result = middleware.wrap_tool_call(request, lambda _req: expected)

    assert result is expected


@pytest.mark.anyio
async def test_awrap_tool_call_blocks_non_kb_tool_when_selection_exists():
    middleware = KnowledgeBaseOnlyMiddleware()
    request = _tool_request("web_fetch", runtime=_runtime(["kb-1"]), tool_call_id="tc-async")

    async def handler(_req):
        raise AssertionError("handler should not be called")

    result = await middleware.awrap_tool_call(request, handler)

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert result.tool_call_id == "tc-async"
    assert result.name == "web_fetch"
