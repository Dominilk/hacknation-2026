# AI Chief of Staff — Architecture

> Organizational intelligence through agentic knowledge graph

**Stack:** Python · FastAPI · OpenAI Agents SDK · chromadb · igraph · Sigma.js

---

## System Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLIENTS    Browser (Sigma.js)  ·  Event Sources  ·  CLI / Gradio  │
├─────────────────────────────────────────────────────────────────────┤
│  API        FastAPI  ─  server.py                                   │
│             POST /ingest  ·  POST /query  ·  GET /graph             │
│             GET /nodes/{name}  ·  WS /ws/updates  ·  POST /optimize │
│             ─── GraphContext (shared dep) ───────────────────────── │
├─────────────────────────────────────────────────────────────────────┤
│  AGENTS     openai-agents SDK                                       │
│             Ingestion Agent  ·  Reader Agent  ·  Optimize Agent     │
├─────────────────────────────────────────────────────────────────────┤
│  TOOLS      @function_tool wrappers                                 │
│             similarity_search · read_node · list_links              │
│             search_nodes · create_node · update_node · graph_stats  │
│             ─── delegates to ──────────────────────────────────────│
│             graph.py · embeddings.py · graph_index.py · models.py   │
├─────────────────────────────────────────────────────────────────────┤
│  STORAGE    graph/nodes/ (markdown)  ·  chromadb  ·  igraph         │
├─────────────────────────────────────────────────────────────────────┤
│  EXTERNAL   OpenAI API  ─  Responses API · Embeddings API           │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
src/
├── server.py            # FastAPI app, endpoints, WebSocket, startup/shutdown
├── models.py            # Pydantic: NodeData, IngestionResult, QueryRequest, ...
├── graph.py             # Read/write markdown files, parse [[wikilinks]], frontmatter
├── embeddings.py        # OAI embed API → chromadb upsert/query
├── graph_index.py       # igraph wrapper: build from files, algorithms, incremental update
├── tools.py             # @function_tool wrappers for agents (via RunContextWrapper)
├── context.py           # GraphContext dataclass (shared dependency)
└── agents/
    ├── ingest.py        # Ingestion agent: event → search → traverse → update graph
    ├── query.py         # Reader agent: question → search → traverse → response
    └── optimize.py      # Optimize agent: graph health, merge, prune, link (stretch)
graph/
├── nodes/               # Flat markdown files = knowledge graph nodes
│   ├── alice.md
│   ├── auth-migration.md
│   └── ...
└── _index/
    └── chroma/          # chromadb persistent storage
seeds/                   # Synthetic events for demo
frontend/                # Sigma.js + Graphology graph visualization
pyproject.toml
```

## Shared Context

All agents and tools share a `GraphContext` via the OAI Agents SDK's `RunContextWrapper`:

```python
@dataclass
class GraphContext:
    graph_dir: Path            # path to graph/nodes/
    chroma_collection: Collection  # chromadb collection
    graph_index: igraph.Graph  # in-memory graph
    openai_client: AsyncOpenAI # for embedding calls
```

## Agents

### Ingestion Agent (`agents/ingest.py`)

- **Model:** gpt-4.1
- **Output type:** `IngestionResult` (nodes_created, nodes_updated, links_added)
- **Tools:** similarity_search, read_node, list_links, search_nodes, **create_node**, **update_node**
- **Instructions:** Process event. Search graph for relevant context. Follow wikilinks to understand relationships. Create/update nodes only for concepts with lasting reference value.

### Reader Agent (`agents/query.py`)

- **Model:** gpt-4.1
- **Output type:** plain text
- **Tools:** similarity_search, read_node, list_links, search_nodes (read-only)
- **Instructions:** Dynamic, based on perspective parameter:
  - **CEO** → wide traversal, shallow depth, strategic summary
  - **PM** → balanced depth, project-focused
  - **Engineer** → narrow traversal, deep technical detail
  - **New Joiner** → onboarding context, "previously on..." recap

### Optimize Agent (`agents/optimize.py`) — stretch

- **Model:** gpt-4.1
- **Output type:** `OptimizeResult`
- **Tools:** all read tools + merge_nodes, archive_node, add_link, graph_stats, find_communities
- **Tasks:** Merge near-duplicates, detect contradictions, flag stale nodes, suggest missing links, small-world health check

## Tools (`tools.py`)

All tools are `@function_tool` with `RunContextWrapper[GraphContext]`:

| Tool | Type | Delegates to | Description |
|------|------|-------------|-------------|
| `similarity_search(query, top_k, filters)` | read | embeddings.py | Cosine similarity via chromadb |
| `read_node(name)` | read | graph.py | Full node content + frontmatter |
| `list_links(name)` | read | graph.py | Outlinks + backlinks of a node |
| `search_nodes(keyword)` | read | graph.py | Full-text substring search |
| `create_node(name, type, content)` | write | graph.py + embeddings.py | Create markdown file + embed |
| `update_node(name, content)` | write | graph.py + embeddings.py | Update file + re-embed |
| `graph_stats()` | read | graph_index.py | Node/edge count, clustering, components |

## Storage

### Markdown Nodes (`graph/nodes/`)

Source of truth. Each node is a file:

```markdown
---
type: person
created: 2026-02-07T14:30:00
updated: 2026-02-07T15:45:00
tags: [engineering, backend]
---

# Alice

Lead engineer on [[auth-migration]].
Works with [[bob]] on [[backend-api]].
Reports to [[carol]].
```

- YAML frontmatter = metadata (type, timestamps, tags)
- `[[wikilinks]]` in content = edges (parsed via regex)
- Types are agent-assigned, not hardcoded: person, project, topic, decision, insight, goal, team, ...

### Chromadb (`graph/_index/chroma/`)

- Persistent local storage
- Embeddings via OAI `text-embedding-3-small` (1536 dims)
- Embedding content = `f"# {title}\n\n{body}"` (title + content for better matching)
- Metadata stored alongside: type, tags, updated
- Cosine similarity search with optional metadata filters

### igraph (in-memory)

- Rebuilt from `[[wikilinks]]` on startup
- Incrementally updated on node create/update
- Algorithms: PageRank, betweenness centrality, community detection (Leiden), shortest paths, clustering coefficient
- Exported as JSON for Sigma.js visualization

---

## API Specification

### `POST /ingest`

Ingest an organizational event into the knowledge graph.

**Request:**
```json
{
  "content": "Meeting notes: Alice and Bob discussed moving auth from sessions to JWT. Decision: use RS256 for distributed verification. Timeline: complete by Q2 launch.",
  "source": "meeting",
  "participants": ["alice", "bob"],
  "timestamp": "2026-02-07T14:00:00Z",
  "metadata": {}
}
```

**Response:**
```json
{
  "nodes_created": [
    {"name": "jwt-decision", "type": "decision"}
  ],
  "nodes_updated": [
    {"name": "auth-migration", "changes": "Added JWT decision and timeline"},
    {"name": "alice", "changes": "Added link to jwt-decision"}
  ],
  "links_added": [
    {"from": "jwt-decision", "to": "auth-migration"},
    {"from": "jwt-decision", "to": "alice"},
    {"from": "jwt-decision", "to": "bob"},
    {"from": "jwt-decision", "to": "q2-launch"}
  ]
}
```

### `POST /query`

Query the knowledge graph with a perspective-aware question.

**Request:**
```json
{
  "question": "What changed today?",
  "perspective": "ceo",
  "scope": null
}
```

`perspective`: `"ceo"` | `"pm"` | `"engineer"` | `"new_joiner"` | custom string

`scope` (optional): limit to a project, team, or topic name.

**Response:**
```json
{
  "answer": "Two key developments today:\n\n1. **Auth Migration** — Team decided to adopt JWT with RS256 signing, replacing session-based auth. This affects the backend API and aligns with the Q2 launch timeline.\n\n2. **ML Pipeline v2** — Data team completed the feature store migration. No blockers remaining.\n\nNo conflicting decisions detected. Both changes are on track for Q2.",
  "sources": ["jwt-decision", "auth-migration", "ml-pipeline-v2", "q2-launch"],
  "traversal_depth": 3
}
```

### `GET /graph`

Export the full graph for visualization.

**Query params:**
- `format`: `"sigma"` (default) | `"json"` | `"gexf"`
- `include_content`: `false` (default) | `true`
- `filter_type`: optional, e.g. `"person"`, `"decision"`

**Response (`format=sigma`):**
```json
{
  "nodes": [
    {
      "key": "alice",
      "attributes": {
        "label": "Alice",
        "type": "person",
        "tags": ["engineering", "backend"],
        "size": 12,
        "color": "#06b6d4",
        "x": 0.42,
        "y": 0.73,
        "pagerank": 0.034,
        "community": 2
      }
    }
  ],
  "edges": [
    {
      "source": "alice",
      "target": "auth-migration",
      "attributes": {
        "weight": 1
      }
    }
  ],
  "stats": {
    "node_count": 47,
    "edge_count": 128,
    "communities": 4,
    "avg_clustering": 0.42,
    "avg_path_length": 2.8
  }
}
```

### `GET /nodes/{name}`

Read a single node with its neighborhood.

**Response:**
```json
{
  "name": "auth-migration",
  "type": "project",
  "created": "2026-02-05T10:00:00Z",
  "updated": "2026-02-07T14:30:00Z",
  "tags": ["engineering", "backend", "security"],
  "content": "# Auth Migration\n\nMigrating from session-based auth to [[jwt-decision|JWT tokens]].\nLed by [[alice]], supported by [[bob]].\n\nPart of [[q2-launch]] deliverables.",
  "outlinks": ["jwt-decision", "alice", "bob", "q2-launch"],
  "backlinks": ["backend-api", "security-review-2026-01"],
  "pagerank": 0.028,
  "community": 2
}
```

### `POST /optimize`

Trigger graph optimization (stretch goal).

**Request:**
```json
{
  "checks": ["duplicates", "orphans", "contradictions", "staleness", "missing_links"]
}
```

**Response:**
```json
{
  "duplicates_merged": [
    {"kept": "jwt-decision", "merged": "jwt-auth-choice", "similarity": 0.97}
  ],
  "orphans_found": ["old-roadmap-draft"],
  "contradictions": [
    {
      "node_a": "jwt-decision",
      "node_b": "security-review-2026-01",
      "description": "JWT decision says RS256, security review recommends ES256"
    }
  ],
  "stale_nodes": ["onboarding-doc-v1"],
  "suggested_links": [
    {"from": "ml-pipeline-v2", "to": "data-team", "reason": "referenced in 3 events but not linked"}
  ]
}
```

### `WebSocket /ws/updates`

Real-time graph change notifications for the visualization frontend.

**Server → Client messages:**

```json
{
  "type": "node_created",
  "node": {"key": "jwt-decision", "attributes": {"label": "JWT Decision", "type": "decision", "color": "#10b981"}},
  "edges": [
    {"source": "jwt-decision", "target": "auth-migration"},
    {"source": "jwt-decision", "target": "alice"}
  ]
}
```

```json
{
  "type": "node_updated",
  "node": "auth-migration",
  "changes": {"content": true, "links_added": ["jwt-decision"], "links_removed": []}
}
```

```json
{
  "type": "graph_stats",
  "stats": {"node_count": 48, "edge_count": 132, "communities": 4}
}
```

---

## Data Flow

```
INGEST:  Event → POST /ingest → Ingestion Agent
           → embed event (OAI) → similarity search (chromadb) → top-k nodes
           → agentic traversal (read nodes, follow [[wikilinks]])
           → decide: create/update nodes
           → write markdown + upsert chromadb + update igraph
           → broadcast changes via WebSocket

QUERY:   Question → POST /query → Reader Agent
           → embed question → similarity search → top-k nodes
           → agentic traversal (perspective-aware depth)
           → synthesize answer from gathered context

VISUALIZE: Browser → GET /graph → igraph export → Sigma.js render
           Browser ← WS /ws/updates ← real-time node/edge changes

OPTIMIZE:  POST /optimize → Optimize Agent
           → graph_stats (igraph algorithms)
           → scan for duplicates, orphans, contradictions
           → merge/prune/link → write changes
```

## Dependencies

```toml
[project]
dependencies = [
    "fastapi",
    "uvicorn",
    "openai-agents",
    "openai",
    "chromadb",
    "igraph",
    "pyyaml",
    "pydantic",
]

[project.optional-dependencies]
viz = ["sigma.js via frontend/"]
dev = ["httpx", "pytest"]
```
