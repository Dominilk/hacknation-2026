# Handoff: Foundation Orchestrator

You are the team lead for building the AI Chief of Staff prototype — an organizational knowledge graph with agentic ingestion.

**Your role: orchestrate, don't implement.** Use delegate mode. Create a team, assign research and implementation tasks, synthesize findings, and present plans to the user (Max) for approval before any code gets written.

**Max wants to be in the loop for all architecture and design decisions.** Present plans, get approval, then execute. Don't make design calls autonomously — discuss first.

---

## Project Context

This is a hackathon project (~24h). We're building a system where:
- Organizational events (meetings, slack, PRs, docs) arrive as structured XML (serialized from Pydantic models)
- AI agents process events, search an existing knowledge graph, and create/update knowledge nodes
- The knowledge graph is flat markdown files with `[[wikilinks]]` — Zettelkasten-style
- Version history via git, with worktrees for parallel agent execution
- Events are also stored as nodes (raw event verbatim) — enabling provenance and cross-referencing
- Queries are perspective-aware (CEO gets different answer than engineer)

### Partner's Work (Dominik)

Dominik is building event ingestors separately. His code is already in the repo:

**`shared/`** — shared Pydantic models (workspace package):
```python
class IngestEvent(BaseModel):
    content: str
    timestamp: datetime
    metadata: Dict[str, str] = {}
```
This model gets serialized to XML for the agents. It may evolve (more fields like source, event_type, participants). Adapt if it changes.

**`ingestors/common/`** — shared ingestor utilities:
- `IngestAPIClient` — async httpx client that POSTs to our `/ingest` endpoint
- This is our API contract: ingestors send `IngestEvent` JSON to `POST /ingest`

**`ingestors/file/`** — file upload ingestor (PDF, DOCX, TXT extraction)

**Root `pyproject.toml`** — uv workspace:
```toml
[tool.uv.workspace]
members = ["shared", "ingestors/common", "ingestors/file"]
```
Our core service needs to be added as a workspace member.

**We own:** core service (FastAPI, graph, embeddings, agents, git ops, tools, visualization later)
**Dominik owns:** ingestors, event sources, shared models

### Key Architectural Decisions (already made — don't revisit)

- **No YAML frontmatter** on nodes. Pure markdown + wikilinks. Agent writes whatever it wants.
- **Events are nodes** — stored verbatim in markdown code blocks. System creates them automatically, agents read them via tools.
- **Git worktrees from day 1** — each agent run gets its own worktree. Commit per ingestion. Merge to main = audit log.
- **Two conflict types**: git merge conflicts AND semantic conflicts (contradictory info detected by agents). Both → resolution agent → escalate to human if needed.
- **Ingest format**: `IngestEvent` Pydantic model (from `shared/`) serialized to XML. Event producers decide batching.
- **Multi-tenant model** (future): each team has own graph. Cross-team sharing via human-approved reports → events.
- **Provider agnostic**: infrastructure layer (graph.py, embeddings.py, git_ops.py) has zero SDK coupling. Only tools.py + agents/ are OpenAI-specific.
- **Notification via natural language** (future): users specify what they care about in natural language, agent matches against notification queue.

### Tech Stack

- Python >=3.13, FastAPI, OpenAI Agents SDK (`openai-agents`), chromadb, Sigma.js (later)
- uv workspace (shared package for models between ingestors and core)
- Git operations via `asyncio.create_subprocess_exec` (zero deps, natively async)
- Embeddings: OpenAI `text-embedding-3-small`
- LLM: `gpt-4.1`

---

## MUST READ Files

Read ALL of these before doing anything:

1. `agent/knowledge/initial-architecture.md` — the full revised architecture spec
2. `agent/tasks/2026-02-08-foundation-scaffold.md` — detailed foundation task with interfaces
3. `agent/tasks/2026-02-08-agent-design.md` — agent design task (Max owns decisions)
4. `agent/tasks/2026-02-07-chief-of-staff-prototype.md` — tracking task with all discussion/decisions
5. `agent/knowledge/openai-agents-sdk.md` — SDK patterns reference from prior research
6. `docs/flows.md` — Mermaid flow diagrams (ingestion, query, conflict resolution, architecture)
7. `shared/src/shared/models.py` — the shared IngestEvent model
8. `ingestors/common/src/common/ingest_client.py` — how ingestors call our API

---

## Phase 1: Research + Planning

**Goal: produce a comprehensive implementation plan for Max to review.**

Create a team with 3 research teammates (all Opus, never Sonnet). Use delegate mode.

### Research Tasks

**Teammate 1 — OpenAI Agents SDK Deep Dive:**
- Read the architecture files listed above, understand our system design
- Research OpenAI Agents SDK with our specific use case in mind:
  - How to implement the worktree pattern: agent runs in a worktree context, commits, then system merges. How does `RunContextWrapper` handle the worktree-specific `GraphContext`?
  - How to get the agent to produce a commit message as part of structured output (`IngestionResult` with `commit_message` field)
  - Tool design: what should each tool return? How verbose? How to format for optimal agent comprehension?
  - `call_model_input_filter` — how to trim context during long graph traversals
  - `agent.as_tool()` for potential sub-agents (entity extraction, conflict detection)
  - Dynamic instructions for the query agent (inject perspective into system prompt)
  - Lifecycle hooks for logging/tracing agent behavior
- Fetch latest docs: https://openai.github.io/openai-agents-python/ (tools, context, running_agents, agents pages)
- Output: concrete recommendations with code patterns for our specific system

**Teammate 2 — Infrastructure Patterns:**
- Read the architecture and foundation task files
- Research git worktree patterns for our use case:
  - Worktree lifecycle (create → work → commit → merge → cleanup)
  - Handling merge conflicts programmatically
  - Concurrent worktree safety (multiple worktrees from same repo)
  - How chromadb interacts with worktrees (chromadb is NOT per-worktree — it's shared. Only markdown files are per-worktree.)
- Research chromadb latest patterns:
  - Persistent client setup, collection management
  - Batch embedding, similarity search with filters
  - How to handle embedding updates when worktree merges change files on main
- Research FastAPI patterns for Python 3.13:
  - Lifespan context management
  - Async endpoint patterns
  - Dependency injection for GraphContext
  - How our core service integrates into the existing uv workspace
- Output: concrete implementation recommendations for each infrastructure module

**Teammate 3 — Agent Design Research:**
- Read architecture files and agent design task
- Research prompting best practices for tool-using agents:
  - How to instruct an agent to search → traverse → decide what's node-worthy
  - How to instruct perspective-aware responses (CEO vs engineer)
  - Common pitfalls with tool-using agents (e.g., tool call loops, context overflow, lazy traversal)
  - How to make agents write good markdown with wikilinks
  - How to make agents write meaningful commit messages
- Research examples of similar systems (knowledge graph agents, organizational intelligence)
- Look at what makes good agent instructions: length, structure, examples, constraints
- Output: draft agent instructions for ingestion and query agents, tool interface recommendations

### Synthesis

After all 3 teammates report back, synthesize their findings into a single **Implementation Plan** document. This should include:

1. **Project structure** (exact files, what goes where, how it fits into the uv workspace)
2. **Module-by-module implementation spec** (graph.py, embeddings.py, git_ops.py, context.py, tools.py, agents/)
3. **Interface contracts** between modules (exact function signatures, types, return values)
4. **Integration with partner's code** (how /ingest accepts IngestEvent, how shared models are used)
5. **Key design decisions** with rationale
6. **Proposed agent instructions** (draft prompts for ingestion + query agents)
7. **Proposed tool interfaces** (exact function signatures, return formats)
8. **Open questions** for Max (things you genuinely need input on)

**Present this plan to Max and wait for approval before proceeding to Phase 2.**

---

## Phase 2: Implementation

**Only start after Max approves the plan from Phase 1.**

### Pre-Implementation

1. Add our core service to the uv workspace (update root `pyproject.toml` members, create our `pyproject.toml`)
3. Create directory structure: `src/` for our core code, `graph/nodes/`, `graph/_index/`
4. Run `uv sync` to verify the workspace works with all packages

### Implementation Tasks (assign to teammates, 1 per module)

Each teammate owns specific files. No two teammates edit the same file.

**Teammate A — Graph Core:**
- `src/graph.py` — read/write/update markdown, wikilink parsing, search, links
- `src/context.py` — GraphContext dataclass with worktree fork support
- Smoke tests for graph operations

**Teammate B — Embeddings + Git:**
- `src/embeddings.py` — chromadb embed/search/reindex
- `src/git_ops.py` — init, worktree create/remove, commit, merge, log, diff
- Smoke tests for both

**Teammate C — Tools + Agents + Server:**
- `src/tools.py` — `@function_tool` wrappers (depends on A + B, so starts after or works from agreed interfaces)
- `src/agents/ingest.py` — ingestion agent with stub/draft prompt (Max will refine)
- `src/agents/query.py` — query agent with stub/draft prompt (Max will refine)
- `src/server.py` — FastAPI app with endpoints, ingestion orchestration (worktree lifecycle)
- Accepts `IngestEvent` from partner's ingestors on `POST /ingest`

### Integration

After all teammates finish:
- Verify end-to-end: create a test event, ingest it, check graph files + git log + chromadb, query it
- Fix any integration issues
- Verify `uv sync` and `uv run` work across the whole workspace

---

## Phase 3: Agent Design (discuss with Max first)

After implementation is working end-to-end, present agent design research findings to Max:
- Draft ingestion agent prompt
- Draft query agent prompt
- Tool interface analysis (what's working, what's missing)
- Recommendations for agent behavior tuning

Max will discuss and iterate on these with you before finalizing. He owns this domain.

---

## Important Notes

- **Always use Opus for teammates.** Never Sonnet. The user explicitly requested this.
- **Present plans before implementing.** Max wants to be in the loop for design decisions.
- **Read ALL the MUST READ files** before creating tasks or spawning teammates.
- **The graph/ directory will be its own git repo** (separate from the project's git repo). The agent's git operations (worktrees, commits, merges) are on the GRAPH repo, not the project repo. Don't confuse the two.
- **Chromadb is shared** across worktrees — only markdown files live in worktrees. Chromadb updates should happen after merge to main (or handle this carefully — this is a design question for the plan).
- **The shared/ package** contains models used by both ingestors and our core service. Import from it, don't duplicate models.
- **Don't touch ingestors/** — that's Dominik's domain.
- **Do things yourself instead of telling Max to do them.** He's busy. If something needs doing and you can do it, do it (after getting plan approval for the overall approach).

## Team Configuration

- **Team name**: `chief-of-staff`
- **Lead**: orchestrator (you) — delegate mode, coordination only
- **Teammates**: 3 for research phase (Opus), 2-3 for implementation (Opus), can reuse
- **Working directory**: `/home/max/repos/github/Dominilk/hacknation-2026`
