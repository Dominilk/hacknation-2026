---
status: active
started: 2026-02-08
---

# Task: Agent Design — Tools, Ingestion Agent, Query Agent

Parent: [[2026-02-07-chief-of-staff-prototype]]
Depends on: [[2026-02-08-foundation-scaffold]]

## Intent

Design and implement the agent layer: tool interfaces, ingestion agent, and query agent. This is where the intelligence lives.

**Max owns design decisions** — prompting strategy, tool semantics, agent behavior, how agents think about the graph.

## Scope

### 1. Tool interfaces (`src/tools.py`)

Wrap graph/embeddings/git as `@function_tool` for OpenAI Agents SDK.

Key design questions (for Max):
- **What information do tools return?** Just raw content? Formatted with context? How much should we pre-process vs let the agent figure out?
- **Tool granularity** — is `list_links` worth having as a separate tool, or does `read_node` already show enough context? Start minimal, add tools when agents demonstrably need them.
- **create_node vs update_node** — should the agent decide the name? Or should we have the agent propose and the system slugify?

V0 tool set:
| Tool | Description |
|------|-------------|
| `similarity_search(query, top_k)` | Cosine search via chromadb |
| `read_node(name)` | Full node content |
| `list_links(name)` | Outlinks + backlinks |
| `search_nodes(keyword)` | Full-text search |
| `create_node(name, content)` | Create markdown + embed |
| `update_node(name, content)` | Update markdown + re-embed |
| `get_recent_changes(since)` | Git log |

### 2. Ingestion agent (`src/agents/ingest.py`)

The core agent. Receives XML events, decides what's node-worthy, updates the graph.

Key design:
- **Instructions prompt** — the heart of the system. How to guide the agent to: search first, explore via wikilinks, decide what matters, write good nodes, link appropriately.
- **Output** — after processing, the agent should produce a git commit message summarizing what changed and why. This becomes the version history.
- **Threshold judgment** — what crosses from "noise" to "lasting knowledge"? This is instructed, not coded.

### 3. Query agent (`src/agents/query.py`)

Answers questions by traversing the graph. Perspective-aware.

Key design:
- **Perspective system** — how to instruct the agent to modulate depth/breadth based on role (CEO, engineer, PM, new joiner). Dynamic instructions? System prompt template?
- **Traversal strategy** — agent starts with similarity search, follows wikilinks. How deep? How wide? Agent decides based on instructions.
- **Source attribution** — should the response cite which nodes it drew from?

## Done When

- [ ] Tool wrappers work with RunContextWrapper[GraphContext]
- [ ] Ingestion agent can process an XML event and update the graph
- [ ] Ingestion agent writes meaningful git commit messages
- [ ] Query agent answers questions with perspective-appropriate responses
- [ ] End-to-end: ingest event → query about it → get sensible answer

## Sources

**Knowledge files:**
- [[initial-architecture]] — architecture spec

**External docs:**
- MUST READ: [OpenAI Agents SDK — Tools](https://openai.github.io/openai-agents-python/tools/)
- MUST READ: [OpenAI Agents SDK — Context](https://openai.github.io/openai-agents-python/context/)
- MUST READ: [OpenAI Agents SDK — Running Agents](https://openai.github.io/openai-agents-python/running_agents/)
