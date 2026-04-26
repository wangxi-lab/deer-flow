"""Middleware to inject selected external RAG resources into agent context."""

from __future__ import annotations

from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from deerflow.config.rag_config import get_rag_config


def get_selected_resource_ids_from_runtime(runtime: Runtime) -> list[str]:
    """Return thread-selected knowledge-base resource ids from runtime context/config."""
    context = runtime.context or {}
    value = context.get("rag_resource_ids")
    if isinstance(value, list):
        selected = [item for item in value if isinstance(item, str) and item.strip()]
        if selected:
            return selected

    runtime_config = getattr(runtime, "config", None) or {}
    configurable = runtime_config.get("configurable", {})
    value = configurable.get("rag_resource_ids")
    if isinstance(value, list):
        selected = [item for item in value if isinstance(item, str) and item.strip()]
        if selected:
            return selected

    try:
        from langgraph.config import get_config

        configurable = get_config().get("configurable", {})
    except RuntimeError:
        configurable = {}

    value = configurable.get("rag_resource_ids")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


class RAGSelectionMiddleware(AgentMiddleware[AgentState]):
    """Inject selected external knowledge-base resource ids into the last user message."""

    def _get_selected_resource_ids(self, runtime: Runtime) -> list[str]:
        return get_selected_resource_ids_from_runtime(runtime)

    def _build_selection_message(self, resource_ids: list[str]) -> str:
        provider = get_rag_config().provider or "external_rag"
        lines = [
            "<selected_knowledge_bases>",
            f"The current thread already has external knowledge-base resources selected for provider `{provider}`.",
            "Use `local_search` to search these selected resources. When you omit `resource_ids`, the selected resources are applied automatically.",
            "Knowledge-base-only mode is active for this thread.",
            "You must answer using only evidence returned from `local_search` against the selected resources.",
            "Do not use web search, web fetch, uploaded files, MCP tools, or prior model knowledge as factual support while this mode is active.",
            "If the selected knowledge base does not contain enough evidence, clearly say that the answer was not found in the selected knowledge base.",
            "Selected resource ids:",
        ]
        for resource_id in resource_ids:
            lines.append(f"- {resource_id}")
        lines.append("Do not ask the user which knowledge base to use unless they explicitly ask to change it.")
        lines.append("</selected_knowledge_bases>")
        return "\n".join(lines)

    @override
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict | None:
        messages = list(state.get("messages", []))
        if not messages:
            return None

        last_index = len(messages) - 1
        last_message = messages[last_index]
        if not isinstance(last_message, HumanMessage):
            return None

        selected_resource_ids = self._get_selected_resource_ids(runtime)
        if not selected_resource_ids:
            return None

        selection_message = self._build_selection_message(selected_resource_ids)
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
