# AI Chief of Staff — Architecture

> Organizational intelligence through agentic knowledge graph

**Stack:** Python 3.12 · FastAPI · OpenAI Agents SDK · chromadb · Sigma.js

---

## Core Idea

The graph has two layers: raw events and distilled knowledge. Events are also nodes — linked to the knowledge they produce. Agents decide what crosses the threshold from noise into lasting knowledge.

### Core Loop

1. Event arrives (message, meeting, PR, doc, decision) as structured XML
2. System creates event node (raw XML stored verbatim) in a git worktree
3. Ingestion agent searches graph for relevant context (similarity search → wikilink traversal)
4. Agent creates/updates knowledge nodes, links them back to event node
5. Agent commits in worktree with descriptive message
6. Merge worktree → main (merge commit = audit log)
7. If merge conflict → conflict resolution agent; if unresolvable → notify stakeholder

### Parallelism

Any number of update agents can run concurrently — each gets its own git worktree. Same for optimize agents. Git merge semantics handle convergence. Conflict resolution is agentic.

### Reading / Output

- Perspective-aware queries — same question, different answers for CEO vs engineer vs PM
- Abstraction pyramid — CEO gets wide/shallow, IC gets narrow/deep
- "What changed today?" — git history + agent synthesis
- "New joiner context" — instant onboarding briefing from the graph
- Contradiction/conflict detection across knowledge

### The Graph

- Flat markdown + wikilinks (Zettelkasten-style, human-readable)
- **No frontmatter, no prescribed structure.** Agent writes whatever it wants.
- Two node types by convention (not enforced): event nodes (raw data) and knowledge nodes (distilled)
- Entity types discovered organically by agents, not hardcoded
- Embeddings index (chromadb) for similarity search
- Version history via git — worktrees for parallelism, merge commits as audit trail
- Interactive visualization via Sigma.js (later)

---

## Storage

### Markdown Nodes (`graph/nodes/`)

Source of truth. Knowledge nodes are plain markdown with wikilinks:

```markdown
# Auth Migration

The team decided to move from session-based auth to JWT tokens.
This affects [[alice]], [[backend-api]], and [[q2-launch]].

Key decision: Use RS256 signing to allow distributed verification.
See also [[security-review-2026-01]].

Source: [[event-2026-02-08-auth-meeting]]
```

Event nodes store raw XML verbatim:

````markdown
# Event: Auth Migration Meeting

```xml
<event type="meeting" source="zoom" timestamp="2026-02-08T10:00:00Z">
  <participants>
    <person>Alice Chen</person>
    <person>Bob Martinez</person>
  </participants>
  <content>
    Meeting about auth migration. Decision: move to JWT with RS256...
  </content>
</event>
```
````

Events as nodes enables:
- **Provenance**: trace any knowledge back to source events
- **Cross-referencing**: agents link slack messages to meetings to PRs — no consumer-side logic
- **Reprocessing**: re-ingest from event nodes if agents improve

### Chromadb (`graph/_index/`)

- Persistent local storage
- Embeddings via OpenAI `text-embedding-3-small`
- Content embedded as `f"# {title}\n\n{body}"`
- Cosine similarity search

### Git (version history + parallelism)

- Graph directory is a git repo. `main` branch = source of truth.
- Each agent run gets a **worktree** branched from main
- Agent commits in its worktree, then merges back to main
- Merge commit message = audit log (what changed and WHY)
- Merge conflicts → conflict resolution agent → escalate to human if needed
- `git log` = timeline of organizational events
- History queries power "what changed?" features

---

## Agents

### Ingestion Agent

- Receives: XML event
- Worktree: gets its own, branched from main
- Steps:
  1. Create event node (raw XML verbatim)
  2. Search graph for relevant context (similarity + wikilink traversal)
  3. Create/update knowledge nodes, link back to event node
  4. Commit with descriptive message
- Output: `IngestionResult` with `commit_message`, `nodes_created`, `nodes_updated`

### Query Agent (Reader)

- Receives: question + perspective (role/abstraction level)
- Tools: read-only (similarity_search, read_node, list_links, search_nodes, get_recent_changes)
- Behavior: Traverse graph to answer questions. Tailor response to perspective.

### Optimize Agent (stretch)

- Own worktree, merges back to main
- Merge near-duplicates, detect contradictions, prune stale nodes
- Can run in parallel with ingestion agents

### Conflict Resolution Agent

- Triggered on merge conflicts
- Reads both sides of the conflict, resolves if possible
- If unresolvable → notify stakeholder

---

## Tools (V0)

| Tool | Type | Description |
|------|------|-------------|
| `similarity_search(query, top_k)` | read | Cosine similarity via chromadb |
| `read_node(name)` | read | Full node content |
| `list_links(name)` | read | Outlinks + backlinks |
| `search_nodes(keyword)` | read | Full-text substring search |
| `create_node(name, content)` | write | Create markdown file + embed |
| `update_node(name, content)` | write | Update file + re-embed |
| `get_recent_changes(since)` | read | Git log — what changed recently |

Start with these. Add tools as we discover agents need them.

---

## API (V0)

| Endpoint | Description |
|----------|-------------|
| `POST /ingest` | XML event → worktree → ingestion agent → merge |
| `POST /query` | Question + perspective → reader agent → answer |
| `GET /graph` | Export graph for visualization |
| `GET /nodes/{name}` | Read a single node with links |

Event producers decide batching: slack messages batched, meeting transcripts trigger immediately.

---

## Ingest Format

Events arrive as XML with whatever metadata the source provides:

```xml
<event type="meeting" source="zoom" timestamp="2026-02-08T10:00:00Z">
  <participants>
    <person>Alice Chen</person>
    <person>Bob Martinez</person>
  </participants>
  <content>
    Meeting about auth migration. Decision: move to JWT with RS256...
  </content>
</event>
```

The agent processes the full XML and decides what's node-worthy. No hardcoded extraction.

---

## Shared Context

```python
@dataclass
class GraphContext:
    graph_dir: Path           # path to nodes/ in this worktree
    graph_root: Path          # path to worktree root (or main graph root for queries)
    chroma_collection: Collection
    openai_client: AsyncOpenAI
```

Passed to all tools via `RunContextWrapper[GraphContext]`.

---

## Data Flow

```
INGEST:  XML Event → POST /ingest
           → create git worktree from main
           → create event node (raw XML)
           → Ingestion Agent: similarity search → agentic traversal → create/update nodes
           → commit in worktree (agent-written message)
           → merge worktree → main (audit log in merge commit)
           → conflict? → resolution agent or stakeholder notification
           → clean up worktree

QUERY:   Question → POST /query → Reader Agent
           → similarity search → top-k nodes
           → agentic traversal (perspective-aware)
           → synthesize answer from gathered context
           (reads from main branch, no worktree needed)

VIZ:     Browser → GET /graph → export nodes + wikilinks → Sigma.js
```

---

## Dependencies

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn",
    "openai-agents",
    "openai",
    "chromadb",
    "pydantic",
]
```
