"""Middleware to enforce knowledge-base-only tool usage when KB resources are selected."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from deerflow.agents.middlewares.rag_selection_middleware import get_selected_resource_ids_from_runtime

_ALLOWED_TOOL_NAMES = frozenset({"ask_clarification", "local_search"})


class KnowledgeBaseOnlyMiddleware(AgentMiddleware[AgentState]):
    """Restrict the agent to KB-backed retrieval when thread-selected KBs are active."""

    def _is_active(self, runtime: object | None) -> bool:
        if runtime is None:
            return False
        return bool(get_selected_resource_ids_from_runtime(runtime))

    def _filter_tools(self, request: ModelRequest) -> ModelRequest:
        if not self._is_active(getattr(request, "runtime", None)):
            return request

        allowed_tools = [tool for tool in request.tools if getattr(tool, "name", None) in _ALLOWED_TOOL_NAMES]
        return request.override(tools=allowed_tools)

    def _build_block_message(self, request: ToolCallRequest) -> ToolMessage:
        tool_name = str(request.tool_call.get("name") or "unknown_tool")
        tool_call_id = str(request.tool_call.get("id") or "missing_tool_call_id")
        return ToolMessage(
            content=(
                f"Knowledge-base-only mode is active for this thread. Tool '{tool_name}' is disabled. "
                "Use `local_search` with the selected knowledge-base resources only. "
                "If the knowledge base does not contain enough evidence, tell the user that directly."
            ),
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

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
        if self._is_active(getattr(request, "runtime", None)) and request.tool_call.get("name") not in _ALLOWED_TOOL_NAMES:
            return self._build_block_message(request)
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if self._is_active(getattr(request, "runtime", None)) and request.tool_call.get("name") not in _ALLOWED_TOOL_NAMES:
            return self._build_block_message(request)
        return await handler(request)
