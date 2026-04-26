"""Middleware to enforce user-selected Skill execution paths."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import Command

_BASE_ALLOWED_TOOL_NAMES = frozenset({"ask_clarification", "read_file"})
_KNOWLEDGE_BASE_QA_TOOL_NAMES = frozenset(
    {
        "ask_clarification",
        "read_file",
        "tool_search",
        "vikingdb_kb_search_knowledge",
        "vikingdb_kb_list_resources",
        "vikingdb_kb_health",
    }
)
_CORRECTION_MARKER = "[SELECTED_SKILL_ROUTE_REQUIRED]"


def get_selected_skill_names_from_runtime(runtime: Runtime) -> list[str]:
    """Return user-selected Skill names from runtime context/config."""
    context = runtime.context or {}
    value = context.get("selected_skill_names")
    selected = _normalize_skill_names(value)
    if selected:
        return selected

    runtime_config = getattr(runtime, "config", None) or {}
    configurable = runtime_config.get("configurable", {})
    selected = _normalize_skill_names(configurable.get("selected_skill_names"))
    if selected:
        return selected

    try:
        from langgraph.config import get_config

        configurable = get_config().get("configurable", {})
    except RuntimeError:
        configurable = {}

    return _normalize_skill_names(configurable.get("selected_skill_names"))


def _normalize_skill_names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    names: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _normalize_tool_call_args(raw_args: object) -> dict:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class SelectedSkillMiddleware(AgentMiddleware[AgentState]):
    """Force selected Skills to be loaded and followed before answering."""

    def _get_selected_skill_names(self, runtime: Runtime | object | None) -> list[str]:
        if runtime is None:
            return []
        return get_selected_skill_names_from_runtime(runtime)  # type: ignore[arg-type]

    def _build_selection_message(self, selected_skill_names: list[str]) -> str:
        skill_list = ", ".join(f"`{name}`" for name in selected_skill_names)
        lines = [
            "<selected_skill_route>",
            "The user explicitly selected a Skill route in the UI.",
            f"Selected Skill(s): {skill_list}.",
            "This is an execution constraint, not a suggestion.",
            "Do not answer directly from prior knowledge.",
            "Do not use web search or unrelated tools unless the selected Skill explicitly instructs you to do so.",
            "Your next action must call `read_file` for each selected Skill's `SKILL.md` under `/mnt/skills`.",
            "After reading the selected Skill instructions, follow that workflow exactly.",
            "If the selected Skill is `knowledge-base-qa`, call `vikingdb_kb_search_knowledge` and answer only from returned chunks.",
            "If the required Skill file or MCP tool is unavailable, say the selected Skill route cannot be executed instead of answering from general knowledge.",
            "</selected_skill_route>",
        ]
        return "\n".join(lines)

    def _has_selected_skill_read(self, state: AgentState, selected_skill_names: list[str]) -> bool:
        selected = set(selected_skill_names)
        for message in state.get("messages", []):
            if getattr(message, "type", None) != "ai":
                continue
            for tool_call in getattr(message, "tool_calls", None) or []:
                if tool_call.get("name") != "read_file":
                    continue
                args = _normalize_tool_call_args(tool_call.get("args", {}))
                path = str(args.get("path") or "")
                if "/mnt/skills/" not in path.replace("\\", "/"):
                    continue
                if any(f"/{skill_name}/SKILL.md" in path.replace("\\", "/") for skill_name in selected):
                    return True
        return False

    def _has_vikingdb_search(self, state: AgentState) -> bool:
        for message in state.get("messages", []):
            if getattr(message, "type", None) != "ai":
                continue
            for tool_call in getattr(message, "tool_calls", None) or []:
                if tool_call.get("name") == "vikingdb_kb_search_knowledge":
                    return True
        return False

    def _allowed_tool_names(self, state: AgentState, selected_skill_names: list[str]) -> frozenset[str]:
        if not self._has_selected_skill_read(state, selected_skill_names):
            return _BASE_ALLOWED_TOOL_NAMES
        if "knowledge-base-qa" in selected_skill_names and not self._has_vikingdb_search(state):
            return _KNOWLEDGE_BASE_QA_TOOL_NAMES
        return _KNOWLEDGE_BASE_QA_TOOL_NAMES if "knowledge-base-qa" in selected_skill_names else _BASE_ALLOWED_TOOL_NAMES

    def _filter_tools(self, request: ModelRequest) -> ModelRequest:
        runtime = getattr(request, "runtime", None)
        selected_skill_names = self._get_selected_skill_names(runtime)
        if not selected_skill_names:
            return request

        state = getattr(request, "state", None) or {}
        allowed = self._allowed_tool_names(state, selected_skill_names)
        allowed_tools = [tool for tool in request.tools if getattr(tool, "name", None) in allowed]

        # If a deployment exposes none of the route tools, do not hide everything;
        # the prompt/correction path will produce a clear failure message.
        if not allowed_tools:
            return request
        return request.override(tools=allowed_tools)

    def _build_block_message(self, request: ToolCallRequest) -> ToolMessage:
        tool_name = str(request.tool_call.get("name") or "unknown_tool")
        tool_call_id = str(request.tool_call.get("id") or "missing_tool_call_id")
        return ToolMessage(
            content=(
                f"Selected Skill mode is active. Tool '{tool_name}' is disabled for this step. "
                "First read the selected Skill's SKILL.md. For knowledge-base-qa, use "
                "`vikingdb_kb_search_knowledge` and answer only from returned chunks."
            ),
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    @override
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict | None:
        messages = list(state.get("messages", []))
        if not messages:
            return None

        last_index = len(messages) - 1
        last_message = messages[last_index]
        if not isinstance(last_message, HumanMessage):
            return None

        selected_skill_names = self._get_selected_skill_names(runtime)
        if not selected_skill_names:
            return None

        selection_message = self._build_selection_message(selected_skill_names)
        original_content = last_message.content
        if isinstance(original_content, str):
            updated_content = f"{selection_message}\n\n{original_content}"
        elif isinstance(original_content, list):
            updated_content = [{"type": "text", "text": f"{selection_message}\n\n"}, *original_content]
        else:
            updated_content = original_content

        messages[last_index] = HumanMessage(
            content=updated_content,
            id=last_message.id,
            additional_kwargs=last_message.additional_kwargs,
        )
        return {"messages": messages}

    def _build_correction(self, selected_skill_names: list[str]) -> HumanMessage:
        skill_list = ", ".join(selected_skill_names)
        return HumanMessage(
            content=(
                f"{_CORRECTION_MARKER} You must execute the selected Skill route ({skill_list}) before answering. "
                "Do not provide a direct answer. Call `read_file` for the selected SKILL.md now. "
                "For knowledge-base-qa, then call `vikingdb_kb_search_knowledge` and answer only from returned chunks."
            )
        )

    def _needs_correction(self, state: AgentState, runtime: Runtime) -> bool:
        selected_skill_names = self._get_selected_skill_names(runtime)
        if not selected_skill_names:
            return False
        if self._has_selected_skill_read(state, selected_skill_names):
            return False

        messages = state.get("messages", [])
        if not messages:
            return False

        if any(getattr(message, "type", None) == "human" and _CORRECTION_MARKER in str(getattr(message, "content", "")) for message in messages):
            return False

        last_message = messages[-1]
        if getattr(last_message, "type", None) != "ai":
            return False
        return not bool(getattr(last_message, "tool_calls", None))

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        if not self._needs_correction(state, runtime):
            return None
        return {"messages": [self._build_correction(self._get_selected_skill_names(runtime))]}

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self.after_model(state, runtime)

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        return handler(self._filter_tools(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        return await handler(self._filter_tools(request))

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        selected_skill_names = self._get_selected_skill_names(getattr(request, "runtime", None))
        if selected_skill_names and request.tool_call.get("name") not in _KNOWLEDGE_BASE_QA_TOOL_NAMES:
            return self._build_block_message(request)
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        selected_skill_names = self._get_selected_skill_names(getattr(request, "runtime", None))
        if selected_skill_names and request.tool_call.get("name") not in _KNOWLEDGE_BASE_QA_TOOL_NAMES:
            return self._build_block_message(request)
        return await handler(request)
