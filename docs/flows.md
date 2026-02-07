# System Flows

## Ingestion Flow

The primary flow. Event → knowledge graph update.

```mermaid
flowchart TD
    E[/"XML Event arrives<br/>(via POST /ingest)"/] --> WT["Create git worktree<br/>from main branch"]
    WT --> EN["Create event node<br/>(raw XML verbatim)"]
    EN --> AGENT["Run Ingestion Agent<br/>in worktree context"]

    subgraph agent ["Ingestion Agent Loop"]
        direction TB
        A1["Read event node"] --> A2["Similarity search<br/>(chromadb)"]
        A2 --> A3["Read top-k nodes"]
        A3 --> A4["Follow wikilinks<br/>to build context"]
        A4 --> A5{"Semantic conflict<br/>detected?"}
        A5 -- "No" --> A6["Create/update<br/>knowledge nodes"]
        A5 -- "Yes, resolvable" --> A6
        A5 -- "Unresolvable" --> NOTIFY1["Flag for stakeholder<br/>notification"]
        NOTIFY1 --> A6
        A6 --> A7["Link knowledge nodes<br/>back to event node"]
        A7 --> A8["Produce IngestionResult<br/>with commit_message"]
    end

    AGENT --> agent
    agent --> COMMIT["Commit in worktree<br/>(agent-written message)"]
    COMMIT --> MERGE{"Merge worktree<br/>→ main"}
    MERGE -- "Clean merge" --> AUDIT["Merge commit =<br/>audit log entry"]
    MERGE -- "Conflict" --> RESOLVE{"Conflict Resolution<br/>Agent"}
    RESOLVE -- "Resolved" --> AUDIT
    RESOLVE -- "Unresolvable" --> NOTIFY2["Notify stakeholder"]
    NOTIFY2 --> AUDIT
    AUDIT --> CLEANUP["Remove worktree<br/>+ delete branch"]
    CLEANUP --> DONE(["Done"])
```

## Parallel Ingestion

Multiple events processed concurrently. Each gets its own worktree.

```mermaid
flowchart LR
    subgraph events ["Event Sources"]
        S1["Slack batch"]
        S2["Meeting transcript"]
        S3["PR merged"]
    end

    subgraph worktrees ["Git Worktrees (parallel)"]
        W1["worktree-1<br/>Agent A"]
        W2["worktree-2<br/>Agent B"]
        W3["worktree-3<br/>Agent C"]
    end

    S1 --> W1
    S2 --> W2
    S3 --> W3

    W1 --> M["main branch<br/>(merge sequentially)"]
    W2 --> M
    W3 --> M
```

## Query Flow

Read-only. No worktree needed — reads from main.

```mermaid
flowchart TD
    Q[/"Question + Perspective<br/>(via POST /query)"/] --> AGENT["Run Query Agent<br/>on main branch"]

    subgraph agent ["Query Agent Loop"]
        direction TB
        Q1["Similarity search<br/>(chromadb)"] --> Q2["Read top-k nodes"]
        Q2 --> Q3["Follow wikilinks<br/>(depth varies by perspective)"]
        Q3 --> Q4["Check recent changes<br/>(git log)"]
        Q4 --> Q5["Synthesize answer<br/>(perspective-aware)"]
    end

    AGENT --> agent
    agent --> RESP(["Response with<br/>source attribution"])
```

## Conflict Resolution

Handles both git merge conflicts and semantic conflicts.

```mermaid
flowchart TD
    subgraph types ["Conflict Types"]
        GIT["Git merge conflict<br/>(same file edited<br/>in parallel worktrees)"]
        SEM["Semantic conflict<br/>(contradictory information<br/>across events/nodes)"]
    end

    GIT --> CRAGENT["Conflict Resolution<br/>Agent"]
    SEM --> CRAGENT

    CRAGENT --> SEARCH["Search graph for<br/>additional context"]
    SEARCH --> DECIDE{"Can resolve<br/>with confidence?"}
    DECIDE -- "Yes" --> RESOLVE["Apply resolution<br/>+ explain reasoning"]
    DECIDE -- "No" --> ESCALATE["Notify stakeholder<br/>with context + options"]
    RESOLVE --> LOG["Record resolution<br/>in commit message"]
    ESCALATE --> WAIT["Await human input"]
    WAIT --> LOG
```

## Component Architecture

```mermaid
flowchart TB
    subgraph clients ["Clients"]
        API["REST API<br/>(FastAPI)"]
        VIZ["Sigma.js<br/>Visualization"]
    end

    subgraph agents ["Agent Layer"]
        IA["Ingestion<br/>Agent"]
        QA["Query<br/>Agent"]
        OA["Optimize<br/>Agent"]
        CRA["Conflict Resolution<br/>Agent"]
    end

    subgraph tools ["Tool Layer"]
        RT["Read Tools<br/>similarity_search, read_node<br/>list_links, search_nodes<br/>get_recent_changes"]
        WT["Write Tools<br/>create_node<br/>update_node"]
    end

    subgraph infra ["Infrastructure"]
        GRAPH["graph.py<br/>Markdown R/W<br/>Wikilink parsing"]
        EMBED["embeddings.py<br/>Chromadb"]
        GIT["git_ops.py<br/>Worktrees, commits<br/>merge, log"]
        CTX["context.py<br/>GraphContext"]
    end

    subgraph storage ["Storage"]
        MD["graph/nodes/<br/>Markdown files"]
        CHROMA["graph/_index/<br/>Chromadb"]
        GITREPO[".git/<br/>Version history"]
    end

    API --> IA & QA
    VIZ --> API
    IA & QA & OA & CRA --> RT & WT
    RT & WT --> GRAPH & EMBED & GIT
    GRAPH & EMBED & GIT --> CTX
    GRAPH --> MD
    EMBED --> CHROMA
    GIT --> GITREPO
