import type { Message } from "@langchain/langgraph-sdk";
import { ChevronDownIcon, FileIcon, Loader2Icon } from "lucide-react";
import {
  memo,
  useMemo,
  useState,
  type AnchorHTMLAttributes,
  type ImgHTMLAttributes,
} from "react";
import rehypeKatex from "rehype-katex";

import { Loader } from "@/components/ai-elements/loader";
import {
  Message as AIElementMessage,
  MessageContent as AIElementMessageContent,
  MessageResponse as AIElementMessageResponse,
  MessageToolbar,
} from "@/components/ai-elements/message";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import { Task, TaskTrigger } from "@/components/ai-elements/task";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { resolveArtifactURL } from "@/core/artifacts/utils";
import { useI18n } from "@/core/i18n/hooks";
import {
  extractContentFromMessage,
  extractReasoningContentFromMessage,
  extractTextFromMessage,
  findToolCallResult,
  hasContent,
  hasToolCalls,
  parseUploadedFiles,
  stripUploadedFilesTag,
  type FileInMessage,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import { humanMessagePlugins } from "@/core/streamdown";
import { cn } from "@/lib/utils";

import { CopyButton } from "../copy-button";

import { MarkdownContent } from "./markdown-content";
import { MessageTokenUsage } from "./message-token-usage";

type LocalSearchChunk = {
  text?: string;
  score?: number;
  source_id?: string;
  source_title?: string;
  source_uri?: string | null;
  chunk_id?: string;
};

type NumberedLocalSearchChunk = LocalSearchChunk & {
  citationIndex: number;
};

export function MessageListItem({
  className,
  message,
  allMessages,
  isLoading,
  threadId,
  tokenUsageEnabled = false,
}: {
  className?: string;
  message: Message;
  allMessages?: Message[];
  isLoading?: boolean;
  threadId: string;
  tokenUsageEnabled?: boolean;
}) {
  const isHuman = message.type === "human";
  return (
    <AIElementMessage
      className={cn("group/conversation-message relative w-full", className)}
      from={isHuman ? "user" : "assistant"}
    >
      <MessageContent
        className={isHuman ? "w-fit" : "w-full"}
        message={message}
        allMessages={allMessages}
        isLoading={isLoading}
        threadId={threadId}
        tokenUsageEnabled={tokenUsageEnabled}
      />
      {!isLoading && (
        <MessageToolbar
          className={cn(
            isHuman ? "-bottom-9 justify-end" : "-bottom-8",
            "absolute right-0 left-0 z-20 opacity-0 transition-opacity delay-200 duration-300 group-hover/conversation-message:opacity-100",
          )}
        >
          <div className="flex gap-1">
            <CopyButton
              clipboardData={
                extractContentFromMessage(message) ??
                extractReasoningContentFromMessage(message) ??
                ""
              }
            />
          </div>
        </MessageToolbar>
      )}
    </AIElementMessage>
  );
}

/**
 * Custom image component that handles artifact URLs
 */
function MessageImage({
  src,
  alt,
  threadId,
  maxWidth = "90%",
  ...props
}: React.ImgHTMLAttributes<HTMLImageElement> & {
  threadId: string;
  maxWidth?: string;
}) {
  if (!src) return null;

  const imgClassName = cn("overflow-hidden rounded-lg", `max-w-[${maxWidth}]`);

  if (typeof src !== "string") {
    return <img className={imgClassName} src={src} alt={alt} {...props} />;
  }

  const url = src.startsWith("/mnt/") ? resolveArtifactURL(src, threadId) : src;

  return (
    <a href={url} target="_blank" rel="noopener noreferrer">
      <img className={imgClassName} src={url} alt={alt} {...props} />
    </a>
  );
}

function MessageContent_({
  className,
  message,
  allMessages,
  isLoading = false,
  threadId,
  tokenUsageEnabled = false,
}: {
  className?: string;
  message: Message;
  allMessages?: Message[];
  isLoading?: boolean;
  threadId: string;
  tokenUsageEnabled?: boolean;
}) {
  const rehypePlugins = useRehypeSplitWordsIntoSpans(isLoading);
  const isHuman = message.type === "human";
  const components = useMemo(
    () => ({
      img: (props: ImgHTMLAttributes<HTMLImageElement>) => (
        <MessageImage {...props} threadId={threadId} maxWidth="90%" />
      ),
      a: ({ href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) => {
        if (href?.startsWith("/mnt/")) {
          const url = resolveArtifactURL(href, threadId);
          return (
            <a
              {...props}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
            />
          );
        }
        return <a {...props} href={href} />;
      },
    }),
    [threadId],
  );

  const rawContent = extractContentFromMessage(message);
  const reasoningContent = extractReasoningContentFromMessage(message);

  const files = useMemo(() => {
    const files = message.additional_kwargs?.files;
    if (!Array.isArray(files) || files.length === 0) {
      if (rawContent.includes("<uploaded_files>")) {
        // If the content contains the <uploaded_files> tag, we return the parsed files from the content for backward compatibility.
        return parseUploadedFiles(rawContent);
      }
      return null;
    }
    return files as FileInMessage[];
  }, [message.additional_kwargs?.files, rawContent]);

  const contentToDisplay = useMemo(() => {
    if (isHuman) {
      return rawContent ? stripUploadedFilesTag(rawContent) : "";
    }
    return rawContent ?? "";
  }, [rawContent, isHuman]);
  const citedSources = useMemo(
    () =>
      !isHuman && allMessages
        ? extractCitedKnowledgeBaseSources(message, allMessages)
        : [],
    [allMessages, isHuman, message],
  );
  const numberedCitedSources = useMemo<NumberedLocalSearchChunk[]>(
    () =>
      citedSources.map((chunk, index) => ({
        ...chunk,
        citationIndex: index + 1,
      })),
    [citedSources],
  );
  const annotatedContent = useMemo(
    () =>
      !isHuman
        ? annotateContentWithKnowledgeBaseCitations(
            contentToDisplay,
            numberedCitedSources,
          )
        : contentToDisplay,
    [contentToDisplay, isHuman, numberedCitedSources],
  );

  const filesList =
    files && files.length > 0 ? (
      <RichFilesList files={files} threadId={threadId} />
    ) : null;

  // Uploading state: mock AI message shown while files upload
  if (message.additional_kwargs?.element === "task") {
    return (
      <AIElementMessageContent className={className}>
        <Task defaultOpen={false}>
          <TaskTrigger title="">
            <div className="text-muted-foreground flex w-full cursor-default items-center gap-2 text-sm select-none">
              <Loader className="size-4" />
              <span>{contentToDisplay}</span>
            </div>
          </TaskTrigger>
        </Task>
      </AIElementMessageContent>
    );
  }

  // Reasoning-only AI message (no main response content yet)
  if (!isHuman && reasoningContent && !rawContent) {
    return (
      <AIElementMessageContent className={className}>
        <Reasoning isStreaming={isLoading}>
          <ReasoningTrigger />
          <ReasoningContent>{reasoningContent}</ReasoningContent>
        </Reasoning>
        <MessageTokenUsage
          enabled={tokenUsageEnabled}
          isLoading={isLoading}
          message={message}
        />
      </AIElementMessageContent>
    );
  }

  if (isHuman) {
    const messageResponse = contentToDisplay ? (
      <AIElementMessageResponse
        remarkPlugins={humanMessagePlugins.remarkPlugins}
        rehypePlugins={humanMessagePlugins.rehypePlugins}
        components={components}
        parseIncompleteMarkdown={false}
      >
        {contentToDisplay}
      </AIElementMessageResponse>
    ) : null;
    return (
      <div className={cn("ml-auto flex flex-col gap-2", className)}>
        {filesList}
        {messageResponse && (
          <AIElementMessageContent className="w-fit">
            {messageResponse}
          </AIElementMessageContent>
        )}
      </div>
    );
  }

  return (
    <AIElementMessageContent className={className}>
      {filesList}
      <MarkdownContent
        content={annotatedContent}
        isLoading={isLoading}
        rehypePlugins={[...rehypePlugins, [rehypeKatex, { output: "html" }]]}
        className="my-3"
        components={components}
      />
      {numberedCitedSources.length > 0 && (
        <KnowledgeBaseCitations chunks={numberedCitedSources} />
      )}
      <MessageTokenUsage
        enabled={tokenUsageEnabled}
        isLoading={isLoading}
        message={message}
      />
    </AIElementMessageContent>
  );
}

function KnowledgeBaseCitations({
  chunks,
}: {
  chunks: NumberedLocalSearchChunk[];
}) {
  const { t } = useI18n();

  return (
    <div className="mt-4 flex flex-col gap-3">
      <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
        {t.toolCalls.citedKnowledgeBaseSources} ({chunks.length})
      </div>
      <div className="flex flex-col gap-2">
        {chunks.map((chunk, index) => (
          <KnowledgeBaseCitationCard
            key={`${chunk.source_id ?? "source"}-${chunk.chunk_id ?? index}`}
            chunk={chunk}
          />
        ))}
      </div>
    </div>
  );
}

function KnowledgeBaseCitationCard({
  chunk,
}: {
  chunk: NumberedLocalSearchChunk;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const title =
    chunk.source_title ?? chunk.source_id ?? t.toolCalls.knowledgeBaseSource;

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      id={`kb-source-${chunk.citationIndex}`}
      className="bg-muted/30 rounded-lg border scroll-mt-24"
    >
      <div className="flex items-center gap-2 p-3">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex min-w-0 flex-1 items-center gap-2 text-left"
          >
            <span className="inline-flex shrink-0 rounded-full border px-2 py-0.5 text-xs">
              [{chunk.citationIndex}]
            </span>
            <span className="truncate text-sm font-medium">{title}</span>
            <ChevronDownIcon
              className={cn(
                "text-muted-foreground ml-auto size-4 shrink-0 transition-transform",
                open ? "rotate-180" : "",
              )}
            />
          </button>
        </CollapsibleTrigger>
        {typeof chunk.score === "number" && (
          <div className="text-muted-foreground hidden shrink-0 text-xs sm:block">
            {t.toolCalls.relevanceScore(chunk.score)}
          </div>
        )}
      </div>
      <CollapsibleContent>
        <div className="border-t px-3 pt-2 pb-3">
          {chunk.source_id && (
            <div className="text-muted-foreground mb-2 text-xs">
              {chunk.source_id}
            </div>
          )}
          {typeof chunk.score === "number" && (
            <div className="text-muted-foreground mb-2 text-xs sm:hidden">
              {t.toolCalls.relevanceScore(chunk.score)}
            </div>
          )}
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
              {truncateText(chunk.text, 280)}
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function extractCitedKnowledgeBaseSources(
  message: Message,
  allMessages: Message[],
): LocalSearchChunk[] {
  if (message.type !== "ai" || !hasContent(message) || hasToolCalls(message)) {
    return [];
  }

  const messageIndex = allMessages.findIndex((item) => item.id === message.id);
  if (messageIndex <= 0) {
    return [];
  }

  const collected: LocalSearchChunk[] = [];
  const seen = new Set<string>();

  for (let index = messageIndex - 1; index >= 0; index -= 1) {
    const previous = allMessages[index];
    if (!previous) {
      continue;
    }

    if (previous.type === "human") {
      break;
    }

    if (previous.type === "ai") {
      for (const toolCall of previous.tool_calls ?? []) {
        if (!isKnowledgeBaseSearchToolName(toolCall.name) || !toolCall.id) {
          continue;
        }
        const result = findToolCallResult(toolCall.id, allMessages);
        const chunks = parseLocalSearchChunks(result);
        for (const chunk of chunks) {
          const dedupeKey = `${chunk.source_id ?? ""}:${chunk.chunk_id ?? chunk.text ?? ""}`;
          if (seen.has(dedupeKey)) {
            continue;
          }
          seen.add(dedupeKey);
          collected.push(chunk);
        }
      }
      continue;
    }

    if (previous.type === "tool") {
      const toolResultText = extractTextFromMessage(previous);
      if (toolResultText.includes("Knowledge-base-only mode is active")) {
        continue;
      }
    }
  }

  return collected.slice(0, 4);
}

function parseLocalSearchChunks(result: unknown): LocalSearchChunk[] {
  if (!result) {
    return [];
  }

  if (Array.isArray(result)) {
    return result.filter(isLocalSearchChunk);
  }
  if (isMcpKnowledgeSearchPayload(result)) {
    return result.chunks.filter(isLocalSearchChunk);
  }

  if (typeof result !== "string") {
    return [];
  }

  try {
    const parsed = JSON.parse(result);
    if (Array.isArray(parsed)) {
      return parsed.filter(isLocalSearchChunk);
    }
    if (isMcpKnowledgeSearchPayload(parsed)) {
      return parsed.chunks.filter(isLocalSearchChunk);
    }
    return [];
  } catch {
    return [];
  }
}

function isKnowledgeBaseSearchToolName(name: string): boolean {
  return name === "local_search" || name.endsWith("_search_knowledge");
}

function isMcpKnowledgeSearchPayload(
  value: unknown,
): value is { chunks: unknown[] } {
  return (
    typeof value === "object" &&
    value !== null &&
    Array.isArray((value as { chunks?: unknown }).chunks)
  );
}

function isLocalSearchChunk(value: unknown): value is LocalSearchChunk {
  return typeof value === "object" && value !== null;
}

function annotateContentWithKnowledgeBaseCitations(
  content: string,
  chunks: NumberedLocalSearchChunk[],
): string {
  if (!content || chunks.length === 0) {
    return content;
  }

  const segments = content.split(/(```[\s\S]*?```)/g);
  let sentenceIndex = 0;

  return segments
    .map((segment) => {
      if (segment.startsWith("```") && segment.endsWith("```")) {
        return segment;
      }

      return segment
        .split("\n")
        .map((line) => annotateLineWithCitations(line, chunks, () => sentenceIndex++))
        .join("\n");
    })
    .join("");
}

function annotateLineWithCitations(
  line: string,
  chunks: NumberedLocalSearchChunk[],
  nextSentenceIndex: () => number,
): string {
  const trimmed = line.trim();
  if (!trimmed) {
    return line;
  }

  if (
    trimmed.startsWith("#") ||
    trimmed.startsWith(">") ||
    trimmed.startsWith("- ") ||
    trimmed.startsWith("* ") ||
    /^\d+\.\s/.test(trimmed) ||
    trimmed.startsWith("|")
  ) {
    return line;
  }

  const sentencePattern = /[^。！？!?]+[。！？!?]?/g;
  return line.replace(sentencePattern, (segment) => {
    const leadingWhitespace = /^\s*/.exec(segment)?.[0] ?? "";
    const trailingWhitespace = /\s*$/.exec(segment)?.[0] ?? "";
    const core = segment.trim();
    if (!core) {
      return segment;
    }

    const chunk = chunks[nextSentenceIndex() % chunks.length];
    if (!chunk) {
      return segment;
    }
    const href = chunk.source_uri ?? `#kb-source-${chunk.citationIndex}`;
    const marker = `[\\[${chunk.citationIndex}\\]](${href})`;
    const needsSpace = /[A-Za-z0-9)`]$/.test(core);
    return `${leadingWhitespace}${core}${needsSpace ? " " : ""}${marker}${trailingWhitespace}`;
  });
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1).trimEnd()}...`;
}

/**
 * Get file extension and check helpers
 */
const getFileExt = (filename: string) =>
  filename.split(".").pop()?.toLowerCase() ?? "";

const FILE_TYPE_MAP: Record<string, string> = {
  json: "JSON",
  csv: "CSV",
  txt: "TXT",
  md: "Markdown",
  py: "Python",
  js: "JavaScript",
  ts: "TypeScript",
  tsx: "TSX",
  jsx: "JSX",
  html: "HTML",
  css: "CSS",
  xml: "XML",
  yaml: "YAML",
  yml: "YAML",
  pdf: "PDF",
  png: "PNG",
  jpg: "JPG",
  jpeg: "JPEG",
  gif: "GIF",
  svg: "SVG",
  zip: "ZIP",
  tar: "TAR",
  gz: "GZ",
};

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"];

function getFileTypeLabel(filename: string): string {
  const ext = getFileExt(filename);
  return FILE_TYPE_MAP[ext] ?? (ext.toUpperCase() || "FILE");
}

function isImageFile(filename: string): boolean {
  return IMAGE_EXTENSIONS.includes(getFileExt(filename));
}

/**
 * Format bytes to human-readable size string
 */
function formatBytes(bytes: number): string {
  if (bytes === 0) return "—";
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

/**
 * List of files from additional_kwargs.files (with optional upload status)
 */
function RichFilesList({
  files,
  threadId,
}: {
  files: FileInMessage[];
  threadId: string;
}) {
  if (files.length === 0) return null;
  return (
    <div className="mb-2 flex flex-wrap justify-end gap-2">
      {files.map((file, index) => (
        <RichFileCard
          key={`${file.filename}-${index}`}
          file={file}
          threadId={threadId}
        />
      ))}
    </div>
  );
}

/**
 * Single file card that handles FileInMessage (supports uploading state)
 */
function RichFileCard({
  file,
  threadId,
}: {
  file: FileInMessage;
  threadId: string;
}) {
  const { t } = useI18n();
  const isUploading = file.status === "uploading";
  const isImage = isImageFile(file.filename);

  if (isUploading) {
    return (
      <div className="bg-background border-border/40 flex max-w-50 min-w-30 flex-col gap-1 rounded-lg border p-3 opacity-60 shadow-sm">
        <div className="flex items-start gap-2">
          <Loader2Icon className="text-muted-foreground mt-0.5 size-4 shrink-0 animate-spin" />
          <span
            className="text-foreground truncate text-sm font-medium"
            title={file.filename}
          >
            {file.filename}
          </span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <Badge
            variant="secondary"
            className="rounded px-1.5 py-0.5 text-[10px] font-normal"
          >
            {getFileTypeLabel(file.filename)}
          </Badge>
          <span className="text-muted-foreground text-[10px]">
            {t.uploads.uploading}
          </span>
        </div>
      </div>
    );
  }

  if (!file.path) return null;

  const fileUrl = resolveArtifactURL(file.path, threadId);

  if (isImage) {
    return (
      <a
        href={fileUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="group border-border/40 relative block overflow-hidden rounded-lg border"
      >
        <img
          src={fileUrl}
          alt={file.filename}
          className="h-32 w-auto max-w-60 object-cover transition-transform group-hover:scale-105"
        />
      </a>
    );
  }

  return (
    <div className="bg-background border-border/40 flex max-w-50 min-w-30 flex-col gap-1 rounded-lg border p-3 shadow-sm">
      <div className="flex items-start gap-2">
        <FileIcon className="text-muted-foreground mt-0.5 size-4 shrink-0" />
        <span
          className="text-foreground truncate text-sm font-medium"
          title={file.filename}
        >
          {file.filename}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <Badge
          variant="secondary"
          className="rounded px-1.5 py-0.5 text-[10px] font-normal"
        >
          {getFileTypeLabel(file.filename)}
        </Badge>
        <span className="text-muted-foreground text-[10px]">
          {formatBytes(file.size)}
        </span>
      </div>
    </div>
  );
}

const MessageContent = memo(MessageContent_);
