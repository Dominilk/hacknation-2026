---
status: active
started: 2026-02-08
---

# Task: Foundation — Project Scaffold + Core Layers

Parent: [[2026-02-07-chief-of-staff-prototype]]

## Intent

Set up the fresh project structure and implement the core infrastructure layers that agents and API will build on. This includes the worktree-based git parallelism from day 1.

## Scope

### 1. Project scaffold

Fresh project at repo root (POC stays as `poc/` for reference):

```
pyproject.toml
src/
├── __init__.py
├── server.py          # FastAPI app
├── graph.py           # Markdown read/write, wikilink parsing
├── embeddings.py      # Chromadb integration
├── git_ops.py         # Git worktree + commit + log operations
├── tools.py           # @function_tool wrappers
├── context.py         # GraphContext dataclass
└── agents/
    ├── __init__.py
    ├── ingest.py      # Ingestion agent
    └── query.py       # Query agent
graph/
├── nodes/             # Markdown files (knowledge graph)
└── _index/            # Chromadb persistent storage
seeds/                 # XML events for demo
frontend/              # Sigma.js (later)
```

Dependencies: `fastapi`, `uvicorn`, `openai-agents`, `openai`, `chromadb`, `pydantic`

### 2. Graph core (`src/graph.py`)

Markdown file operations. **No YAML frontmatter** — pure markdown + wikilinks.

```python
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

def read_node(graph_dir: Path, name: str) -> str | None
    # Returns raw markdown content, or None if not found

def write_node(graph_dir: Path, name: str, content: str) -> None
    # Write markdown file. Content is whatever the agent provides.

def update_node(graph_dir: Path, name: str, content: str) -> bool
    # Update existing node. Returns False if not found.

def list_nodes(graph_dir: Path) -> list[str]
    # List all node names (stems of .md files)

def extract_wikilinks(content: str) -> list[str]
    # Parse [[wikilinks]] from content, deduplicated, order-preserving

def get_links(graph_dir: Path, name: str) -> tuple[list[str], list[str]]
    # (outlinks, backlinks) for a node

def search_nodes(graph_dir: Path, keyword: str) -> list[str]
    # Full-text substring search across all nodes
```

Keep it simple. Functions take paths, return data. No classes needed.

### 3. Embeddings (`src/embeddings.py`)

Chromadb integration for similarity search.

```python
EMBED_MODEL = "text-embedding-3-small"

async def embed_node(ctx: GraphContext, name: str, content: str) -> None
    # Embed content as "# {name}\n\n{content}", upsert to chromadb

async def similarity_search(ctx: GraphContext, query: str, top_k: int = 5) -> list[dict]
    # Returns [{name, score, snippet}, ...]

async def remove_embedding(ctx: GraphContext, name: str) -> None

async def reindex_all(ctx: GraphContext) -> None
    # Rebuild index from all nodes on disk
```

### 4. Git operations (`src/git_ops.py`)

Git-based version history with worktree parallelism. Use `asyncio.create_subprocess_exec` — zero deps, natively async.

```python
async def _git(*args: str, cwd: Path) -> str
    # Run git command, return stdout, raise on error

async def init_repo(graph_root: Path) -> None
    # git init if not already a repo

async def create_worktree(graph_root: Path, branch_name: str) -> Path
    # git worktree add /tmp/<branch_name> -b <branch_name>
    # Returns path to worktree

async def remove_worktree(graph_root: Path, worktree_path: Path) -> None
    # git worktree remove <path> && git branch -d <branch>

async def commit(cwd: Path, message: str, paths: list[str] | None = None) -> str
    # Stage paths (or all in nodes/), commit, return hash

async def merge_worktree(graph_root: Path, branch_name: str) -> MergeResult
    # git merge <branch> from main. Returns success/conflict info.
    # MergeResult = dataclass with success: bool, conflicts: list[str], commit_hash: str | None

async def git_log(cwd: Path, since: str | None = None, path: str | None = None, limit: int = 20) -> list[dict]
    # Recent commits. Returns [{hash, message, timestamp, files_changed}, ...]

async def git_diff(cwd: Path, commit: str) -> str
    # What changed in a specific commit
```

**Worktree lifecycle:**
1. `create_worktree(graph_root, "ingest-<uuid>")` → returns `/tmp/ingest-<uuid>/`
2. Agent works in the worktree (creates/updates files in `worktree/nodes/`)
3. `commit(worktree_path, agent_message)`
4. `merge_worktree(graph_root, "ingest-<uuid>")` → merges branch into main
5. `remove_worktree(graph_root, worktree_path)` → cleanup

### 5. Shared context (`src/context.py`)

```python
@dataclass
class GraphContext:
    graph_dir: Path           # path to nodes/ (worktree or main)
    graph_root: Path          # path to repo root (worktree or main)
    chroma_collection: Collection
    openai_client: AsyncOpenAI

    @classmethod
    def create(cls, graph_root: Path) -> "GraphContext":
        # Init chromadb, create collection, return context

    def for_worktree(self, worktree_path: Path) -> "GraphContext":
        # Return new context pointing at worktree's nodes/ dir
        # Same chroma collection + openai client (shared)
```

### 6. Ingestion orchestration (`src/server.py` or separate module)

The system-level orchestration that wraps agent runs:

```python
async def ingest_event(ctx: GraphContext, event_xml: str) -> IngestionResult:
    # 1. Create worktree
    # 2. Create event node (raw XML in markdown code block, auto-named)
    # 3. Create worktree-specific GraphContext
    # 4. Run ingestion agent (passes event node name as input)
    # 5. Commit (agent's commit message from IngestionResult)
    # 6. Merge worktree → main
    # 7. Handle conflicts if any
    # 8. Cleanup worktree
    # 9. Return result
```

The event node creation is SYSTEM infrastructure, not agent work. Agent receives the event node name and reads it like any other node.

## Done When

- [ ] `uv sync` works, project runs
- [ ] Can read/write/update markdown nodes (no frontmatter)
- [ ] Wikilink extraction works
- [ ] Chromadb embedding + similarity search works
- [ ] Git init/worktree/commit/merge/log works
- [ ] GraphContext wires everything together, supports worktree fork
- [ ] Event node auto-creation works (system creates, agent reads)
- [ ] Ingestion orchestration: worktree → agent → commit → merge → cleanup

## Sources

**Knowledge files:**
- [[initial-architecture]] — architecture spec
- [[openai-agents-sdk]] — SDK patterns reference

**External docs:**
- MUST READ: [ChromaDB getting started](https://docs.trychroma.com/docs/overview/getting-started)
- MUST READ: [git worktree docs](https://git-scm.com/docs/git-worktree)
- Reference: [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
