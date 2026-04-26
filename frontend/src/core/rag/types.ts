export interface RAGConfigResponse {
  enabled: boolean;
  provider?: string | null;
  default_resource_ids: string[];
}

export interface RAGHealthResponse {
  enabled: boolean;
  provider?: string | null;
  ok: boolean;
  detail?: string | null;
  metadata: Record<string, unknown>;
}

export interface RAGResource {
  id: string;
  title: string;
  provider: string;
  description?: string | null;
  metadata: Record<string, unknown>;
}

export interface RAGResourcesResponse {
  resources: RAGResource[];
}
