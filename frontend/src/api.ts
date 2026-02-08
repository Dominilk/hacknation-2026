const BASE = '/api';

export interface GraphNode {
  name: string;
  pagerank: number;
  community: number;
  centrality: number;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeDetail {
  name: string;
  content: string;
  outlinks: string[];
  backlinks: string[];
  error?: string;
}

export interface QueryResponse {
  answer: string;
}

export interface TraceStep {
  t: number;
  ts: number;
  action: string;
  tool: string;
  args: Record<string, unknown>;
  result_summary: string;
  nodes: string[];
}

export interface IngestResponse {
  commit_message: string;
  nodes_created: string[];
  nodes_updated: string[];
  trace: TraceStep[];
}

export interface GraphCommit {
  hash: string;
  message: string;
  timestamp: string;
  files_changed: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getGraph: () => request<GraphData>('/graph'),

  getNode: (name: string) => request<NodeDetail>(`/nodes/${encodeURIComponent(name)}`),

  query: (question: string) =>
    request<QueryResponse>('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),

  getCommits: (limit = 100) => request<GraphCommit[]>(`/graph/commits?limit=${limit}`),

  ingest: (content: string) =>
    request<IngestResponse>('/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        timestamp: new Date().toISOString(),
        metadata: { source: 'manual-ui' },
      }),
    }),
};
