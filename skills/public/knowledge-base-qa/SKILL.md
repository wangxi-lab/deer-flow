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
7. Keep the final answer grounded and cite sources at the end.

## Source Format

At the end of the answer, include a compact source list. For each source, keep
the title, `source_id`, and `source_uri` when available.

Example:

```text
来源：
[1] 标题：产品手册
    source_id: doc-123
    source_uri: https://example.com/manual
```
