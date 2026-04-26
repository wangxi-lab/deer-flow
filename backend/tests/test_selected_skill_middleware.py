from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from deerflow.agents.middlewares.selected_skill_middleware import SelectedSkillMiddleware


class _ModelRequest:
    def __init__(self, tools: list[object], runtime: object | None = None, state: dict | None = None):
        self.tools = tools
        self.runtime = runtime
        self.state = state or {}

    def override(self, **updates):
        return _ModelRequest(
            tools=updates.get("tools", self.tools),
            runtime=updates.get("runtime", self.runtime),
            state=updates.get("state", self.state),
        )


def _runtime(skill_names: list[str] | None = None):
    return SimpleNamespace(context={"selected_skill_names": skill_names or []}, config={})


def _tool(name: str):
    return SimpleNamespace(name=name)


def _tool_request(name: str, runtime: object | None = None, tool_call_id: str = "tc-1"):
    return SimpleNamespace(
        tool_call={"name": name, "id": tool_call_id},
        runtime=runtime,
    )


def _skill_read_message(skill_name: str = "knowledge-base-qa") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {"path": f"/mnt/skills/public/{skill_name}/SKILL.md"},
                "id": "read-skill",
            }
        ],
    )


def test_selected_skill_middleware_injects_selected_skill_route() -> None:
    middleware = SelectedSkillMiddleware()
    state = {"messages": [HumanMessage(content="Electron应用怎么打包")]}

    result = middleware.before_agent(state=state, runtime=_runtime(["knowledge-base-qa"]))

    assert result is not None
    updated = result["messages"][-1]
    assert "selected_skill_route" in updated.content
    assert "knowledge-base-qa" in updated.content
    assert "Do not answer directly" in updated.content
    assert "Electron应用怎么打包" in updated.content


def test_selected_skill_middleware_noop_without_selection() -> None:
    middleware = SelectedSkillMiddleware()
    state = {"messages": [HumanMessage(content="Hello")]}

    result = middleware.before_agent(state=state, runtime=_runtime([]))

    assert result is None


def test_wrap_model_call_filters_to_read_file_before_skill_is_read() -> None:
    middleware = SelectedSkillMiddleware()
    request = _ModelRequest(
        tools=[_tool("web_search"), _tool("read_file"), _tool("vikingdb_kb_search_knowledge"), _tool("ask_clarification")],
        runtime=_runtime(["knowledge-base-qa"]),
        state={"messages": [HumanMessage(content="Question")]},
    )

    filtered_names: list[str] = []

    def handler(req):
        filtered_names.extend(tool.name for tool in req.tools)
        return "ok"

    result = middleware.wrap_model_call(request, handler)

    assert result == "ok"
    assert filtered_names == ["read_file", "ask_clarification"]


def test_wrap_model_call_filters_to_vikingdb_after_skill_is_read() -> None:
    middleware = SelectedSkillMiddleware()
    request = _ModelRequest(
        tools=[_tool("web_search"), _tool("read_file"), _tool("vikingdb_kb_search_knowledge"), _tool("ask_clarification")],
        runtime=_runtime(["knowledge-base-qa"]),
        state={"messages": [_skill_read_message()]},
    )

    filtered_names: list[str] = []

    def handler(req):
        filtered_names.extend(tool.name for tool in req.tools)
        return "ok"

    middleware.wrap_model_call(request, handler)

    assert filtered_names == ["read_file", "vikingdb_kb_search_knowledge", "ask_clarification"]


def test_after_model_injects_correction_when_model_answers_without_reading_skill() -> None:
    middleware = SelectedSkillMiddleware()
    state = {
        "messages": [
            HumanMessage(content="Electron应用怎么打包"),
            AIMessage(content="可以用 electron-builder 打包。"),
        ]
    }

    result = middleware.after_model(state=state, runtime=_runtime(["knowledge-base-qa"]))

    assert result is not None
    correction = result["messages"][-1]
    assert "SELECTED_SKILL_ROUTE_REQUIRED" in correction.content
    assert "read_file" in correction.content


def test_after_model_noop_after_skill_is_read() -> None:
    middleware = SelectedSkillMiddleware()
    state = {"messages": [_skill_read_message(), AIMessage(content="ok")]}

    result = middleware.after_model(state=state, runtime=_runtime(["knowledge-base-qa"]))

    assert result is None


def test_wrap_tool_call_blocks_unrelated_tool_when_skill_selected() -> None:
    middleware = SelectedSkillMiddleware()
    request = _tool_request("web_search", runtime=_runtime(["knowledge-base-qa"]))

    result = middleware.wrap_tool_call(request, lambda _req: pytest.fail("handler should not be called"))

    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert result.name == "web_search"
    assert "Selected Skill mode is active" in result.text
