import type { Message } from "@langchain/langgraph-sdk";
import {
  BookOpenTextIcon,
  ChevronUp,
  CircleDotDashedIcon,
  FolderOpenIcon,
  GlobeIcon,
  LightbulbIcon,
  ListTodoIcon,
  MessageCircleQuestionMarkIcon,
  NotebookPenIcon,
  SearchIcon,
  SquareTerminalIcon,
  WrenchIcon,
} from "lucide-react";
import { useMemo, useState, type ComponentType } from "react";

import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import { CodeBlock } from "@/components/ai-elements/code-block";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";
import {
  extractReasoningContentFromMessage,
  findToolCallResult,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import { extractTitleFromMarkdown } from "@/core/utils/markdown";
import { env } from "@/env";
import { cn } from "@/lib/utils";

import { useArtifacts } from "../artifacts";
import { FlipDisplay } from "../flip-display";
import { Tooltip } from "../tooltip";

import { MarkdownContent } from "./markdown-content";

type LocalSearchChunk = {
  text?: string;
  score?: number;
  source_id?: string;
  source_title?: string;
  source_uri?: string | null;
  chunk_id?: string;
};

export function MessageGroup({
  className,
  messages,
  isLoading = false,
}: {
  className?: string;
  messages: Message[];
  isLoading?: boolean;
}) {
  const { t } = useI18n();
  const [showAbove, setShowAbove] = useState(
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true",
  );
  const [showLastThinking, setShowLastThinking] = useState(
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true",
  );
  const steps = useMemo(() => convertToSteps(messages), [messages]);
  const routeSummary = useMemo(
    () => buildRouteSummary(steps, t.toolCalls.answerRouteLabels),
    [steps, t.toolCalls.answerRouteLabels],
  );
  const lastToolCallStep = useMemo(() => {
    const filteredSteps = steps.filter((step) => step.type === "toolCall");
    return filteredSteps[filteredSteps.length - 1];
  }, [steps]);
  const aboveLastToolCallSteps = useMemo(() => {
    if (lastToolCallStep) {
      const index = steps.indexOf(lastToolCallStep);
      return steps.slice(0, index);
    }
    return [];
  }, [lastToolCallStep, steps]);
  const lastReasoningStep = useMemo(() => {
    if (lastToolCallStep) {
      const index = steps.indexOf(lastToolCallStep);
      return steps.slice(index + 1).find((step) => step.type === "reasoning");
    } else {
      const filteredSteps = steps.filter((step) => step.type === "reasoning");
      return filteredSteps[filteredSteps.length - 1];
    }
  }, [lastToolCallStep, steps]);
  const rehypePlugins = useRehypeSplitWordsIntoSpans(isLoading);
  return (
    <ChainOfThought
      className={cn("w-full gap-2 rounded-lg border p-0.5", className)}
      open={true}
    >
      {routeSummary.length > 0 && (
        <div className="border-b px-4 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-muted-foreground flex items-center gap-1.5 text-xs font-medium">
              <CircleDotDashedIcon className="size-3.5" />
              {t.toolCalls.answerRoute}
            </div>
            {routeSummary.map((item) => (
              <span
                key={item.kind}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs",
                  item.className,
                )}
                title={item.detail}
              >
                <item.icon className="size-3" />
                {item.label}
                {item.count > 1 && (
                  <span className="text-muted-foreground">x{item.count}</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}
      {aboveLastToolCallSteps.length > 0 && (
        <Button
          key="above"
          className="w-full items-start justify-start text-left"
          variant="ghost"
          onClick={() => setShowAbove(!showAbove)}
        >
          <ChainOfThoughtStep
            label={
              <span className="opacity-60">
                {showAbove
                  ? t.toolCalls.lessSteps
                  : t.toolCalls.moreSteps(aboveLastToolCallSteps.length)}
              </span>
            }
            icon={
              <ChevronUp
                className={cn(
                  "size-4 opacity-60 transition-transform duration-200",
                  showAbove ? "rotate-180" : "",
                )}
              />
            }
          ></ChainOfThoughtStep>
        </Button>
      )}
      {lastToolCallStep && (
        <ChainOfThoughtContent className="px-4 pb-2">
          {showAbove &&
            aboveLastToolCallSteps.map((step) =>
              step.type === "reasoning" ? (
                <ChainOfThoughtStep
                  key={step.id}
                  label={
                    <MarkdownContent
                      content={step.reasoning ?? ""}
                      isLoading={isLoading}
                      rehypePlugins={rehypePlugins}
                    />
                  }
                ></ChainOfThoughtStep>
              ) : (
                <ToolCall key={step.id} {...step} isLoading={isLoading} />
              ),
            )}
          {lastToolCallStep && (
            <FlipDisplay uniqueKey={lastToolCallStep.id ?? ""}>
              <ToolCall
                key={lastToolCallStep.id}
                {...lastToolCallStep}
                isLast={true}
                isLoading={isLoading}
              />
            </FlipDisplay>
          )}
        </ChainOfThoughtContent>
      )}
      {lastReasoningStep && (
        <>
          <Button
            key={lastReasoningStep.id}
            className="w-full items-start justify-start text-left"
            variant="ghost"
            onClick={() => setShowLastThinking(!showLastThinking)}
          >
            <div className="flex w-full items-center justify-between">
              <ChainOfThoughtStep
                className="font-normal"
                label={t.common.thinking}
                icon={LightbulbIcon}
              ></ChainOfThoughtStep>
              <div>
                <ChevronUp
                  className={cn(
                    "text-muted-foreground size-4",
                    showLastThinking ? "" : "rotate-180",
                  )}
                />
              </div>
            </div>
          </Button>
          {showLastThinking && (
            <ChainOfThoughtContent className="px-4 pb-2">
              <ChainOfThoughtStep
                key={lastReasoningStep.id}
                label={
                  <MarkdownContent
                    content={lastReasoningStep.reasoning ?? ""}
                    isLoading={isLoading}
                    rehypePlugins={rehypePlugins}
                  />
                }
              ></ChainOfThoughtStep>
            </ChainOfThoughtContent>
          )}
        </>
      )}
    </ChainOfThought>
  );
}

function ToolCall({
  id,
  messageId,
  name,
  args,
  result,
  isLast = false,
  isLoading = false,
}: {
  id?: string;
  messageId?: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  isLast?: boolean;
  isLoading?: boolean;
}) {
  const { t } = useI18n();
  const { setOpen, autoOpen, autoSelect, selectedArtifact, select } =
    useArtifacts();

  if (name === "web_search") {
    let label: React.ReactNode = t.toolCalls.searchForRelatedInfo;
    if (typeof args.query === "string") {
      label = t.toolCalls.searchOnWebFor(args.query);
    }
    return (
      <ChainOfThoughtStep key={id} label={label} icon={SearchIcon}>
        {Array.isArray(result) && (
          <ChainOfThoughtSearchResults>
            {result.map((item) => (
              <ChainOfThoughtSearchResult key={item.url}>
                <a href={item.url} target="_blank" rel="noopener noreferrer">
                  {item.title}
                </a>
              </ChainOfThoughtSearchResult>
            ))}
          </ChainOfThoughtSearchResults>
        )}
      </ChainOfThoughtStep>
    );
  } else if (name === "image_search") {
    let label: React.ReactNode = t.toolCalls.searchForRelatedImages;
    if (typeof args.query === "string") {
      label = t.toolCalls.searchForRelatedImagesFor(args.query);
    }
    const results = (
      result as {
        results: {
          source_url: string;
          thumbnail_url: string;
          image_url: string;
          title: string;
        }[];
      }
    )?.results;
    return (
      <ChainOfThoughtStep key={id} label={label} icon={SearchIcon}>
        {Array.isArray(results) && (
          <ChainOfThoughtSearchResults>
            {Array.isArray(results) &&
              results.map((item) => (
                <Tooltip key={item.image_url} content={item.title}>
                  <a
                    className="size-24 overflow-hidden rounded-lg object-cover"
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <div className="bg-accent size-24">
                      <img
                        className="size-full object-cover"
                        src={item.thumbnail_url}
                        alt={item.title}
                        width={100}
                        height={100}
                      />
                    </div>
                  </a>
                </Tooltip>
              ))}
          </ChainOfThoughtSearchResults>
        )}
      </ChainOfThoughtStep>
    );
  } else if (name === "web_fetch") {
    const url = (args as { url: string })?.url;
    let title = url;
    if (typeof result === "string") {
      const potentialTitle = extractTitleFromMarkdown(result);
      if (potentialTitle && potentialTitle.toLowerCase() !== "untitled") {
        title = potentialTitle;
      }
    }
    return (
      <ChainOfThoughtStep
        key={id}
        label={t.toolCalls.viewWebPage}
        icon={GlobeIcon}
      >
        <ChainOfThoughtSearchResult>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="cursor-pointer"
            >
              {title}
            </a>
          )}
        </ChainOfThoughtSearchResult>
      </ChainOfThoughtStep>
    );
  } else if (name === "ls") {
    let description: string | undefined = (args as { description: string })
      ?.description;
    if (!description) {
      description = t.toolCalls.listFolder;
    }
    const path: string | undefined = (args as { path: string })?.path;
    return (
      <ChainOfThoughtStep key={id} label={description} icon={FolderOpenIcon}>
        {path && (
          <ChainOfThoughtSearchResult className="cursor-pointer">
            {path}
          </ChainOfThoughtSearchResult>
        )}
      </ChainOfThoughtStep>
    );
  } else if (name === "read_file") {
    let description: string | undefined = (args as { description: string })
      ?.description;
    if (!description) {
      description = t.toolCalls.readFile;
    }
    const { path } = args as { path: string; content: string };
    return (
      <ChainOfThoughtStep key={id} label={description} icon={BookOpenTextIcon}>
        {path && (
          <ChainOfThoughtSearchResult className="cursor-pointer">
            {path}
          </ChainOfThoughtSearchResult>
        )}
      </ChainOfThoughtStep>
    );
  } else if (name === "local_search") {
    let description: string | undefined = (args as { description: string })
      ?.description;
    const query = (args as { query?: string })?.query;
    if (!description) {
      description = query
        ? t.toolCalls.searchKnowledgeBaseFor(query)
        : t.toolCalls.searchKnowledgeBase;
    }
    const chunks = parseLocalSearchChunks(result);
    return (
      <ChainOfThoughtStep key={id} label={description} icon={BookOpenTextIcon}>
        <div className="mt-2 flex flex-col gap-3">
          {chunks.length === 0 ? (
            <div className="text-muted-foreground text-sm">
              {t.toolCalls.noKnowledgeBaseSources}
            </div>
          ) : (
            chunks.map((chunk, index) => (
              <div
                key={`${chunk.source_id ?? "source"}-${chunk.chunk_id ?? index}`}
                className="bg-muted/30 rounded-lg border p-3"
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">
                      {chunk.source_title ??
                        chunk.source_id ??
                        t.toolCalls.knowledgeBaseSource}
                    </div>
                    {chunk.source_id && (
                      <div className="text-muted-foreground mt-0.5 text-xs">
                        {chunk.source_id}
                      </div>
                    )}
                  </div>
                  {typeof chunk.score === "number" && (
                    <div className="text-muted-foreground shrink-0 text-xs">
                      {t.toolCalls.relevanceScore(chunk.score)}
                    </div>
                  )}
                </div>
                {chunk.source_uri && (
                  <a
                    href={chunk.source_uri}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary mb-2 inline-flex text-xs underline underline-offset-2"
                  >
                    {t.toolCalls.openSource}
                  </a>
                )}
                {chunk.text && (
                  <div className="text-sm whitespace-pre-wrap">
                    {truncateText(chunk.text, 420)}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </ChainOfThoughtStep>
    );
  } else if (name === "write_file" || name === "str_replace") {
    let description: string | undefined = (args as { description: string })
      ?.description;
    if (!description) {
      description = t.toolCalls.writeFile;
    }
    const path: string | undefined = (args as { path: string })?.path;
    if (isLoading && isLast && autoOpen && autoSelect && path && !result) {
      setTimeout(() => {
        const url = new URL(
          `write-file:${path}?message_id=${messageId}&tool_call_id=${id}`,
        ).toString();
        if (selectedArtifact === url) {
          return;
        }
        select(url, true);
        setOpen(true);
      }, 100);
    }

    return (
      <ChainOfThoughtStep
        key={id}
        className="cursor-pointer"
        label={description}
        icon={NotebookPenIcon}
        onClick={() => {
          select(
            new URL(
              `write-file:${path}?message_id=${messageId}&tool_call_id=${id}`,
            ).toString(),
          );
          setOpen(true);
        }}
      >
        {path && (
          <ChainOfThoughtSearchResult className="cursor-pointer">
            {path}
          </ChainOfThoughtSearchResult>
        )}
      </ChainOfThoughtStep>
    );
  } else if (name === "bash") {
    const description: string | undefined = (args as { description: string })
      ?.description;
    if (!description) {
      return t.toolCalls.executeCommand;
    }
    const command: string | undefined = (args as { command: string })?.command;
    return (
      <ChainOfThoughtStep
        key={id}
        label={description}
        icon={SquareTerminalIcon}
      >
        {command && (
          <CodeBlock
            className="mx-0 cursor-pointer border-none px-0"
            showLineNumbers={false}
            language="bash"
            code={command}
          />
        )}
      </ChainOfThoughtStep>
    );
  } else if (name === "ask_clarification") {
    return (
      <ChainOfThoughtStep
        key={id}
        label={t.toolCalls.needYourHelp}
        icon={MessageCircleQuestionMarkIcon}
      ></ChainOfThoughtStep>
    );
  } else if (name === "write_todos") {
    return (
      <ChainOfThoughtStep
        key={id}
        label={t.toolCalls.writeTodos}
        icon={ListTodoIcon}
      ></ChainOfThoughtStep>
    );
  } else {
    const description: string | undefined = (args as { description: string })
      ?.description;
    return (
      <ChainOfThoughtStep
        key={id}
        label={description ?? t.toolCalls.useTool(name)}
        icon={WrenchIcon}
      ></ChainOfThoughtStep>
    );
  }
}

function parseLocalSearchChunks(result: unknown): LocalSearchChunk[] {
  if (!result) {
    return [];
  }
  if (Array.isArray(result)) {
    return result.filter(isLocalSearchChunk);
  }
  if (typeof result !== "string") {
    return [];
  }
  try {
    const parsed = JSON.parse(result);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(isLocalSearchChunk);
  } catch {
    return [];
  }
}

function isLocalSearchChunk(value: unknown): value is LocalSearchChunk {
  return typeof value === "object" && value !== null;
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1).trimEnd()}…`;
}

interface GenericCoTStep<T extends string = string> {
  id?: string;
  messageId?: string;
  type: T;
}

interface CoTReasoningStep extends GenericCoTStep<"reasoning"> {
  reasoning: string | null;
}

interface CoTToolCallStep extends GenericCoTStep<"toolCall"> {
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
}

type CoTStep = CoTReasoningStep | CoTToolCallStep;

type RouteKind = "rag" | "skillMcp" | "mcp" | "web" | "tool";

type RouteSummaryItem = {
  kind: RouteKind;
  label: string;
  detail: string;
  count: number;
  icon: ComponentType<{ className?: string }>;
  className: string;
};

const MCP_NAME_RE = /^[a-zA-Z0-9-]+_[a-zA-Z0-9-]+_/;

function buildRouteSummary(
  steps: CoTStep[],
  labels: {
    rag: string;
    skillMcp: string;
    mcp: string;
    web: string;
    tool: string;
  },
): RouteSummaryItem[] {
  const toolSteps = steps.filter(
    (step): step is CoTToolCallStep => step.type === "toolCall",
  );
  const summaries = new Map<RouteKind, RouteSummaryItem>();

  function add(kind: RouteKind, item: Omit<RouteSummaryItem, "kind" | "count">) {
    const existing = summaries.get(kind);
    if (existing) {
      existing.count += 1;
      return;
    }
    summaries.set(kind, { ...item, kind, count: 1 });
  }

  for (const step of toolSteps) {
    if (step.name === "local_search") {
      add("rag", {
        label: labels.rag,
        detail: step.name,
        icon: BookOpenTextIcon,
        className: "border-emerald-200 bg-emerald-50 text-emerald-700",
      });
    } else if (step.name.startsWith("vikingdb_kb_")) {
      add("skillMcp", {
        label: labels.skillMcp,
        detail: step.name,
        icon: WrenchIcon,
        className: "border-sky-200 bg-sky-50 text-sky-700",
      });
    } else if (step.name === "web_search" || step.name === "web_fetch") {
      add("web", {
        label: labels.web,
        detail: step.name,
        icon: GlobeIcon,
        className: "border-amber-200 bg-amber-50 text-amber-700",
      });
    } else if (MCP_NAME_RE.test(step.name)) {
      add("mcp", {
        label: labels.mcp,
        detail: step.name,
        icon: WrenchIcon,
        className: "border-blue-200 bg-blue-50 text-blue-700",
      });
    } else {
      add("tool", {
        label: labels.tool,
        detail: step.name,
        icon: WrenchIcon,
        className: "border-muted bg-muted/40 text-muted-foreground",
      });
    }
  }

  return ["rag", "skillMcp", "mcp", "web", "tool"]
    .map((kind) => summaries.get(kind as RouteKind))
    .filter((item): item is RouteSummaryItem => Boolean(item));
}

function convertToSteps(messages: Message[]): CoTStep[] {
  const steps: CoTStep[] = [];
  for (const message of messages) {
    if (message.type === "ai") {
      const reasoning = extractReasoningContentFromMessage(message);
      if (reasoning) {
        const step: CoTReasoningStep = {
          id: message.id,
          messageId: message.id,
          type: "reasoning",
          reasoning: extractReasoningContentFromMessage(message),
        };
        steps.push(step);
      }
      for (const tool_call of message.tool_calls ?? []) {
        if (tool_call.name === "task") {
          continue;
        }
        const step: CoTToolCallStep = {
          id: tool_call.id,
          messageId: message.id,
          type: "toolCall",
          name: tool_call.name,
          args: tool_call.args,
        };
        const toolCallId = tool_call.id;
        if (toolCallId) {
          const toolCallResult = findToolCallResult(toolCallId, messages);
          if (toolCallResult) {
            try {
              const json = JSON.parse(toolCallResult);
              step.result = json;
            } catch {
              step.result = toolCallResult;
            }
          }
        }
        steps.push(step);
      }
    }
  }
  return steps;
}
