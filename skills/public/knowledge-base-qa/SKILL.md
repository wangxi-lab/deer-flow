---
name: knowledge-base-qa
description: >-
  Use this skill when the user asks to answer from a knowledge base, internal
  documents, private corpus, enterprise documents, VikingDB, Volcengine
  knowledge base, or private-domain RAG.
---

# Knowledge Base QA

Use this workflow for knowledge-base questions. This is an MCP + Skill path and
does not require the user to select a knowledge base in the DeerFlow UI.

## Workflow

1. Rewrite the user's request into a concise retrieval query.
2. Call the VikingDB MCP search tool, normally exposed by the `vikingdb_kb`
   MCP server as a prefixed name such as `vikingdb_kb_search_knowledge`.
3. If `tool_search.enabled=true`, first use `tool_search` to find the
   `vikingdb_kb` search tool, then call it.
4. Answer only from the chunks returned by the VikingDB MCP search tool.
5. Do not use web search, model prior knowledge, or unrelated tools to fill
   knowledge gaps unless the user explicitly asks for a different mode.
6. If the returned chunks do not provide enough evidence, say clearly:
   "知识库中未找到足够依据。"
7. Keep the final answer grounded. Use short inline citation markers such as
   `[1]` and `[2]` when referring to specific evidence from returned chunks.
8. Do not paste long source excerpts or manually build a verbose source
   appendix. DeerFlow renders source cards from the MCP tool result, including
   document title, relevance score, source link, and related chunk text.

## Source Handling

The MCP tool result contains source metadata in `chunks`. The DeerFlow UI will
render the final source cards from those chunks, so the answer should not
duplicate the full chunk text.

When a brief textual source note is useful, keep it compact and only include
document titles or citation numbers.

Example:

```text
根据知识库，Electron 应用通常可以使用 Electron Builder 或
Electron Forge 打包。[1]

来源：见下方 DeerFlow 自动渲染的知识库来源卡片。
```
