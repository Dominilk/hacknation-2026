# AI Chief of Staff

> Organizational intelligence through an agentic, git-versioned knowledge graph

**Stack:** Python 3.13 &middot; FastAPI &middot; OpenAI Agents SDK &middot; GPT-4.1 &middot; ChromaDB &middot; NetworkX &middot; D3.js &middot; React &middot; TypeScript

Built during HackNation 2026 for the "Superhuman AI Chief of Staff" challenge sponsored by OpenAI.

---

## The Problem

Inside organizations, information flows blindly. Meetings, messages, emails, and documents generate a constant stream of data, but there is no intelligent layer organizing it. Knowledge is scattered, duplicated, or lost. Critical decisions propagate slowly. People are either overwhelmed with irrelevant updates or starved of information they need.

There is no single source of truth, no map of how knowledge moves, and no transparency into who knows what. Existing tools — chat apps, wikis, project management — create silos rather than bridging them. Organizations operate far below their coordination potential.

## The Solution

We built an AI-powered organizational knowledge graph with agentic ingestion. Events from any source (email, Slack, meetings, documents, Discord) are processed by autonomous AI agents that extract entities, decisions, and relationships — building a living, interconnected knowledge base.

The system answers: *Who needs to know this? What is the current truth? What just changed? Where is knowledge blocked or duplicated?*

## Target Audience

Teams and organizations where information is fragmented across communication channels. Executives benefit from high-level "what changed today?" digests; engineers get detailed technical context; new joiners receive instant onboarding briefs — all from the same knowledge graph, tailored to their perspective.

---

## Core Features

### Agentic Ingestion Pipeline

Events arrive via pluggable ingestors (email/IMAP, Discord, file upload, Enron corpus). An AI ingestion agent reads each event, searches the existing graph for relevant context using **semantic similarity + wikilink traversal**, then creates or updates knowledge nodes with rich cross-references. The agent decides what's "node-worthy" — no hardcoded extraction rules.

Every tool call during ingestion is captured via `RunHooks` — action type, arguments, referenced nodes, timing — and visualized on the frontend as a real-time trace animation showing how the agent traverses and builds knowledge.

### Flat-File Knowledge Graph

Knowledge is stored as **plain markdown files with `[[wikilinks]]`** (Zettelkasten-style). This is deliberate:

- **File over app** — plain text is the most durable, portable, composable format. No vendor lock-in, no proprietary databases.
- **The natural medium for AI agents** — LLMs are RL-trained to read, write, and reason about markdown. Standard tools (`grep`, `cat`, `diff`) work out of the box.
- **Git-native** — version control, branching, merging, and diffing come for free.
- **Emergent structure** — agents create connections organically. The graph topology *is* the organization's knowledge structure. No prescribed schema.

Embeddings in ChromaDB (`text-embedding-3-small`) enable cosine similarity search across the graph.

### Git-Based Version History & Parallelism

Every ingestion runs in its own **git worktree**, enabling parallel agent execution. Each produces a commit with an agent-written message explaining what changed and why — creating a full audit trail. `git log` reads like a timeline of organizational knowledge evolution.

Merge conflicts are detected when parallel agents modify the same node. The architecture supports conflict resolution agents that can resolve or escalate to stakeholders.

### Perspective-Aware Queries

Users ask questions in natural language. The query agent traverses the graph (similarity search → read nodes → follow wikilinks 2-3 hops → synthesize) and **adapts its response to the user's role**. An executive gets concise strategic bullets. An engineer gets detailed technical context. A new joiner gets full background explanations. The question text itself conveys perspective — no separate role parameter needed. All answers cite sources via `[[node-name]]` references.

### Interactive Visualization

The frontend renders the knowledge graph as a **D3 force-directed graph** with:

- **Community coloring** — Louvain community detection colors related nodes
- **Importance sizing** — PageRank determines node size
- **Timeline slider** — scrub through git history and watch the graph build commit-by-commit, with autoplay
- **Agent trace animation** — when ingesting, watch each tool call light up nodes in sequence: `search → read → create → update`
- **Clickable wikilinks** — node content renders as markdown with clickable `[[references]]` that navigate the graph

### Multi-Source Ingestors

Pluggable ingestor architecture with a shared `IngestEvent` Pydantic model:

| Ingestor | Source |
|----------|--------|
| **Enron** | Enron email corpus (144k emails, used for demo) |
| **Email** | Generic IMAP/SMTP email polling with batch processing |
| **Discord** | Real-time message batching from Discord channels |
| **File** | Document upload — PDF, DOCX, TXT extraction |

All ingestors feed the same knowledge graph via `POST /ingest`.

---

## Architecture

### Component Overview

```
EVENT SOURCES (email, Slack, meetings, Discord, docs)
         │
         ▼
    AGENT LAYER
    ├── Ingestion Agent — event → knowledge nodes (write, in worktree)
    ├── Query Agent — question → answer with citations (read-only)
    ├── Optimization Agent — deduplication, contradiction detection, pruning
    └── Conflict Resolution Agent — merge conflicts + semantic conflicts
         │
         ▼
    TOOL LAYER
    similarity_search · read_node · list_links · search_nodes
    create_node · update_node · get_recent_changes
         │
         ▼
    STORAGE LAYER
    ├── graph/nodes/*.md — markdown + wikilinks (source of truth)
    ├── graph/_index/ — ChromaDB embeddings (cosine search)
    └── graph/.git/ — version history, worktrees, merge commits
```

### Agent Layer

Built on the **OpenAI Agents SDK**. Agents are defined with typed tools, structured output (Pydantic models), and configurable instructions.

The ingestion agent has 7 tools (5 read, 2 write) and must produce a structured `IngestionResult` with `commit_message`, `nodes_created`, and `nodes_updated`. The query agent is a factory function that injects user perspective into dynamic instructions via closure.

### Infrastructure Layer (Provider-Agnostic)

The infrastructure has **zero SDK coupling**:

- `graph.py` — markdown CRUD, wikilink parsing
- `embeddings.py` — ChromaDB + async OpenAI embeddings
- `git_ops.py` — worktree lifecycle via `asyncio.create_subprocess_exec` (zero external deps)
- `graph_index.py` — NetworkX directed graph with PageRank, Louvain communities, betweenness centrality
- `context.py` — `GraphContext` dataclass shared across all tools

Only `tools.py` and `agents/` are OpenAI-specific. **Swapping LLM providers = rewriting ~2 files.**

### Graph Analytics

The wikilink graph is indexed into a NetworkX `DiGraph` at startup, with lazy-cached analytics:

| Metric | Purpose | Application |
|--------|---------|-------------|
| PageRank | Node importance | Node size in visualization |
| Louvain communities | Topic clusters | Node coloring |
| Betweenness centrality | Information brokers | Identifies key connectors |

The index updates incrementally after each merge — only changed nodes are re-scanned.

### Key Design Decisions

- **No YAML frontmatter on knowledge nodes** — the agent writes whatever it wants in markdown. No prescribed structure.
- **Events are also nodes** — raw content stored verbatim, enabling provenance and cross-referencing. Any knowledge traces back to its source events.
- **Merges serialize via `asyncio.Lock`** while worktree work is fully parallel.
- **Embeddings update incrementally** after merge — diff the commit, re-embed only changed nodes.
- **Graph index invalidates lazily** — analytics recompute only when queried after mutations.

---

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest` | POST | Event → worktree → agent → merge → result + trace |
| `/query` | POST | Question → agent traversal → answer with citations |
| `/graph` | GET | Full graph export (nodes + edges + PageRank + communities) |
| `/graph/commits` | GET | Git log with files_changed per commit (timeline) |
| `/nodes/{name}` | GET | Single node content + outlinks + backlinks |

---

## Architecture Vision

Beyond the current implementation, the architecture is designed for:

**Optimization Agent** — Runs periodically in its own worktree. Detects near-duplicate nodes via embedding similarity, finds contradictions across nodes, identifies stale knowledge with no recent event links, and discovers missing connections between related but unlinked nodes.

**Conflict Resolution Agent** — Handles both git merge conflicts (parallel worktree edits to the same node) and semantic conflicts (contradictory facts across nodes/events). Resolves with confidence or escalates to stakeholders with context and options.

**Stakeholder Notifications** — When new knowledge arrives, determine who needs to know based on the stakeholder graph. Targeted routing based on role, involvement, and knowledge dependencies — not broadcast.

**Identity Resolution** — The same person appears across email, Slack, meetings, code reviews. Build a unified identity graph linking `jeff.dasovich@enron.com` ↔ `Jeff Dasovich` ↔ `@jdasovich` into a single entity.

**Abstraction Pyramid** — The same question answered at different depths. CEO gets the 3-bullet strategic view. Team lead gets operational detail. IC gets full technical context. Controlled by traversal depth and synthesis framing.

**Reprocessing Pipeline** — As agents improve, re-ingest from stored event nodes to refine the knowledge graph without re-fetching source data.

---

## Project Structure

```
├── core/src/core/          # Backend
│   ├── agents/
│   │   ├── ingest.py       # Ingestion agent + prompt
│   │   └── query.py        # Query agent + perspective logic
│   ├── server.py           # FastAPI app + orchestration
│   ├── tools.py            # Agent tool definitions (7 tools)
│   ├── graph.py            # Markdown read/write + wikilink parsing
│   ├── graph_index.py      # NetworkX graph + PageRank + communities
│   ├── embeddings.py       # ChromaDB vector index
│   ├── git_ops.py          # Worktrees, commits, merges
│   ├── tracing.py          # Agent step capture via RunHooks
│   └── context.py          # GraphContext (shared state)
│
├── frontend/src/           # React + TypeScript + D3.js
│   ├── App.tsx             # Grid layout + state management
│   └── components/
│       ├── GraphView.tsx   # D3 force graph + glow effects
│       ├── NodePanel.tsx   # Node detail + markdown rendering
│       ├── QueryPanel.tsx  # Natural language queries
│       ├── IngestPanel.tsx # Event submission + trace viz
│       ├── TimelineSlider.tsx  # Git history scrubber + autoplay
│       └── TraceAnimation.tsx  # Agent step animation
│
├── ingestors/              # Source adapters (workspace packages)
│   ├── common/             # Shared IngestAPIClient
│   ├── enron/              # Enron email corpus
│   ├── email/              # Generic IMAP email
│   ├── discord/            # Discord channels
│   └── file/               # Document upload
│
├── shared/                 # Shared Pydantic models (IngestEvent)
├── graph/                  # Knowledge graph (internal git repo)
│   ├── nodes/              # Markdown files
│   └── _index/             # ChromaDB embeddings
│
└── docs/                   # Architecture documentation + flows
```

UV workspace monorepo: `shared/`, `ingestors/*`, and `core/` are all workspace members with inter-package dependencies.

---

## Running

```bash
# Prerequisites: uv, Node.js

# Install dependencies
uv sync --all-extras
cd frontend && npm install && cd ..

# Start (backend + frontend)
make run
# → http://localhost:5174

# Ingest Enron emails (in another terminal)
make enron-ingest LIMIT=100
```

## Results

- **Working end-to-end pipeline**: events ingested → AI agent searches graph, creates/updates knowledge nodes with wikilinks → git commit with agent-written audit message → perspective-aware queries return tailored answers with source citations
- **Tested with Enron email corpus**: dozens of real corporate emails produce an interconnected knowledge graph of people, decisions, proposals, and events. The agent correctly updates existing nodes without creating duplicates, and links new information to existing context.
- **Multi-source ingestion**: Discord (real-time), email (IMAP polling), file upload (PDF/DOCX/TXT), and Enron corpus all feeding the same knowledge graph
- **Full audit trail**: `git log` reads like a timeline of organizational events with agent-written explanations
- **Interactive visualization**: force-directed graph with community detection, timeline playback, and real-time agent trace animation

The system makes organizational knowledge transparent and interconnected by creating a living knowledge graph from all communication channels. Every piece of knowledge traces back to source events, with full version history enabling "what changed today?" queries backed by actual data. The same graph serves every role with perspective-appropriate responses — eliminating information silos by design.
