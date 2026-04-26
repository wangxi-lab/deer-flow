import { getBackendBaseURL } from "../config";

import type {
  RAGConfigResponse,
  RAGHealthResponse,
  RAGResourcesResponse,
} from "./types";

export async function loadRAGConfig(): Promise<RAGConfigResponse> {
  const res = await fetch(`${getBackendBaseURL()}/api/rag/config`);
  const data = (await res.json()) as Partial<RAGConfigResponse>;
  return {
    enabled: data.enabled ?? false,
    provider: data.provider ?? null,
    default_resource_ids: data.default_resource_ids ?? [],
  };
}

export async function loadRAGHealth(): Promise<RAGHealthResponse> {
  const res = await fetch(`${getBackendBaseURL()}/api/rag/health`);
  const data = (await res.json()) as Partial<RAGHealthResponse>;
  return {
    enabled: data.enabled ?? false,
    provider: data.provider ?? null,
    ok: data.ok ?? false,
    detail: data.detail ?? null,
    metadata: data.metadata ?? {},
  };
}

export async function loadRAGResources(
  query?: string,
): Promise<RAGResourcesResponse> {
  const url = new URL(`${getBackendBaseURL()}/api/rag/resources`);
  if (query?.trim()) {
    url.searchParams.set("query", query.trim());
  }

  const res = await fetch(url.toString());
  const data = (await res.json()) as Partial<RAGResourcesResponse>;
  return {
    resources: data.resources ?? [],
  };
}
