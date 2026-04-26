import { useQuery } from "@tanstack/react-query";

import { loadRAGConfig, loadRAGHealth, loadRAGResources } from "./api";

export function useRAGConfig({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["rag", "config"],
    queryFn: () => loadRAGConfig(),
    enabled,
    refetchOnWindowFocus: false,
  });
}

export function useRAGHealth({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["rag", "health"],
    queryFn: () => loadRAGHealth(),
    enabled,
    refetchOnWindowFocus: false,
  });
}

export function useRAGResources(
  query?: string,
  { enabled = true }: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: ["rag", "resources", query ?? ""],
    queryFn: () => loadRAGResources(query),
    enabled,
    refetchOnWindowFocus: false,
  });
}
