---
status: active
started: 2026-02-07
---

# Task: Prototype AI Chief of Staff — Knowledge Graph with Agentic Ingestion

## Intent

Build a working prototype (hackathon, ~24h) of an organizational knowledge graph that:
1. Ingests events (messages, meetings, PRs, docs, decisions) via structured XML
2. Uses similarity search + agentic graph traversal to find relevant context
3. Updates a flat-file markdown knowledge graph with wikilinks
4. Tracks full version history via git (agent-written commit messages)
5. Can generate perspective-aware answers at different abstraction levels

The system should organically discover entities and relationships — no prescribed structure, no hardcoded types. Bitter lesson: let the agents figure it out.

## Assumptions

- OpenAI stack: Agents SDK, Embeddings API (text-embedding-3-small), GPT-4.1
- Knowledge graph = flat markdown + `[[wikilinks]]`. **No YAML frontmatter.**
- Events arrive as XML with whatever metadata the source provides
- Version history via git — one commit per ingestion batch, agent writes the message
- Prototype scope: ingestion + query. No real integrations (synthetic events).
- Single-user demo. Running locally.

## Work Split

- **Max**: Agent design decisions, prompting, tool design, agent code
- **Partner**: Data sources, event ingestion pipeline, event formats
- **AI agents**: Infrastructure (graph core, embeddings, git ops, API scaffold)

## Subtasks

- [[2026-02-08-foundation-scaffold]] — project structure, graph core, embeddings, git ops
- [[2026-02-08-agent-design]] — tool interfaces, ingestion agent, query agent (Max owns)
- Seed data — XML events for demo (TBD, partner may handle)
- API + wiring — FastAPI endpoints connecting it all (after foundation + agents)
- Visualization — Sigma.js graph viz (later)

## Done When

- [ ] Can ingest an XML event and see the graph update (new nodes, new wikilinks)
- [ ] Git commit after each ingestion with agent-written message
- [ ] Can query the graph and get perspective-aware answers (CEO vs engineer)
- [ ] "What changed today?" works via git history
- [ ] Demo runs end-to-end with seed data
- [ ] (Stretch) Visual graph display
- [ ] (Stretch) Optimization agent

## Sources

**Knowledge files:**
- [[initial-architecture]] — revised architecture spec

**External docs:**
- MUST READ: [OpenAI Agents SDK Quickstart](https://openai.github.io/openai-agents-python/quickstart/)
- MUST READ: [OpenAI Agents SDK — Tools](https://openai.github.io/openai-agents-python/tools/)
- MUST READ: [OpenAI Agents SDK — Context](https://openai.github.io/openai-agents-python/context/)
- MUST READ: [OpenAI Agents SDK — Running Agents](https://openai.github.io/openai-agents-python/running_agents/)
- Reference: [ChromaDB Docs](https://docs.trychroma.com/)

## Considered & Rejected

- **YAML frontmatter on nodes**: Rejected. No prescribed structure — agent writes whatever it wants in markdown. Types/tags/timestamps are not metadata fields, they're emergent from content.
- **JSON ingest format**: XML chosen — richer structure, metadata-friendly, agent parses it naturally.
- **igraph / PageRank / graph algorithms**: Premature. Start with just wikilinks + embeddings. Add complexity when we know what the agents actually need.
- **Neo4j / proper graph DB**: Overkill. Flat files + wikilinks + chromadb is sufficient.
- **Separate edge store**: Wikilinks in content ARE the edges.
- **Commit per tool call**: Too noisy. One commit per ingestion batch is the right granularity.

## Discussion

### Architecture revision (2026-02-08)
Stripped the initial spec down to core. Removed: YAML frontmatter, explicit participants/metadata fields, igraph, overspecified API responses, detailed optimize agent spec. Added: git-based version history, XML ingest format. The principle is minimal tooling, maximum agent autonomy — see what works, add complexity incrementally.

### Events as nodes + parallelism (2026-02-08)
- Events are also nodes in the graph (raw XML stored verbatim). Enables provenance, cross-referencing (agents link slack → meetings → PRs), reprocessing.
- Event node creation is system infrastructure, not agent work. Agent receives event node name, reads it via `read_node`.
- Git worktrees for parallelism from day 1. Each agent run gets its own worktree. Merge commit = audit log.
- Two types of conflicts: git merge conflicts (parallel edits to same file) AND semantic conflicts (contradictory information in events/graph). Both → resolution agent → escalate if needed.

### Notification system (2026-02-08)
- No category/tagging system. Users specify what they care about via natural language prompts ("notify me about decisions affecting Q2 timeline").
- System maintains a notification queue (conflicts, important changes, etc.).
- Agent matches queue items against user preferences.
- Future: privacy/permissions — events carry access metadata, derived nodes inherit restrictions. Propagation rules need agent interpretation with strong specs. Not V0.

### Multi-tenant / privacy model (2026-02-08)
- Each team = its own knowledge graph (own tenant). Full read access for all team members. No per-user ACLs.
- Cross-team sharing: generate a report/view from your graph (human-approved), which becomes an event for another team's graph.
- Federation model: each graph is sovereign. Sharing boundary = human-approved report. Agents in receiving graph process it like any other event.
- Scales by decomposition: 200 teams × 50 users >> 10k users on one graph. Less cross-org small-world connectivity, but much simpler/more scalable.
- Not V0 but shapes architecture: no need for permission metadata on nodes or events within a tenant.

### Provider agnosticism (2026-02-08)
- Starting with OpenAI Agents SDK (hackathon credits), but architecture should allow swapping.
- Infrastructure layer (graph.py, embeddings.py, git_ops.py) has zero SDK coupling.
- Only tools.py and agents/*.py are SDK-specific. Swapping providers = rewriting ~2 files.
- Embeddings function can be made pluggable via GraphContext. Keep simple for V0.
