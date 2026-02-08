import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from pydantic import BaseModel

from agents import Runner
from shared import IngestEvent
from .context import GraphContext, Settings
from . import graph, embeddings
from .git_ops import init_repo, create_worktree, remove_worktree, commit, merge_worktree, git_log
from .agents.ingest import ingestion_agent, IngestionResult
from .agents.query import make_query_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    await init_repo(settings.graph_root)
    app.state.ctx = GraphContext.create(settings)
    app.state.merge_lock = asyncio.Lock()
    yield


app = FastAPI(title="AI Chief of Staff", lifespan=lifespan)


class QueryRequest(BaseModel):
    question: str
    perspective: str = "engineer"


async def ingest_event(ctx: GraphContext, event: IngestEvent, merge_lock: asyncio.Lock) -> IngestionResult:
    """Full ingestion orchestration: worktree -> event node -> agent -> commit -> merge -> cleanup."""
    branch = f"ingest-{uuid4().hex[:8]}"
    worktree = await create_worktree(ctx.graph_root, branch)
    try:
        wt_ctx = ctx.for_worktree(worktree)

        # Create event node (system, not agent)
        ts = event.timestamp.strftime("%Y-%m-%d")
        event_name = f"event-{ts}-{uuid4().hex[:6]}"
        meta_lines = ["type: event", f"timestamp: {event.timestamp.isoformat()}"]
        for k, v in event.metadata.items():
            meta_lines.append(f"{k}: {v}")
        frontmatter = "\n".join(meta_lines)
        event_md = f"---\n{frontmatter}\n---\n\n# Event: {event_name}\n\n```\n{event.content}\n```"
        graph.write_node(wt_ctx.graph_dir, event_name, event_md)

        # Run ingestion agent
        result = await Runner.run(
            ingestion_agent,
            input=f"Process event node: [[{event_name}]]",
            context=wt_ctx,
            max_turns=25,
        )
        output: IngestionResult = result.final_output

        # Commit in worktree
        await commit(worktree, output.commit_message)

        # Merge (serialized via lock)
        async with merge_lock:
            merge = await merge_worktree(ctx.graph_root, branch)

        # Re-embed changed files after merge
        if merge.success:
            log = await git_log(ctx.graph_root, limit=1)
            if log and log[0]["files_changed"]:
                for f in log[0]["files_changed"]:
                    if f.startswith("nodes/") and f.endswith(".md"):
                        node_name = Path(f).stem
                        content = graph.read_node(ctx.graph_dir, node_name)
                        if content:
                            await embeddings.embed_node(ctx, node_name, content)
                        else:
                            await embeddings.remove_embedding(ctx, node_name)

        return output
    finally:
        await remove_worktree(ctx.graph_root, worktree, branch)


@app.post("/ingest")
async def handle_ingest(event: IngestEvent, request: Request) -> dict:
    ctx: GraphContext = request.app.state.ctx
    merge_lock: asyncio.Lock = request.app.state.merge_lock
    result = await ingest_event(ctx, event, merge_lock)
    return result.model_dump()


@app.post("/query")
async def handle_query(req: QueryRequest, request: Request) -> dict:
    ctx: GraphContext = request.app.state.ctx
    agent = make_query_agent(req.perspective)
    result = await Runner.run(agent, input=req.question, context=ctx, max_turns=15)
    return {"answer": result.final_output, "perspective": req.perspective}


@app.get("/graph")
async def handle_graph(request: Request) -> dict:
    """Export graph for visualization: nodes + edges."""
    ctx: GraphContext = request.app.state.ctx
    nodes_list = graph.list_nodes(ctx.graph_dir)
    nodes = []
    edges = []
    for name in nodes_list:
        content = graph.read_node(ctx.graph_dir, name)
        wikilinks = graph.extract_wikilinks(content) if content else []
        nodes.append({"name": name, "content_length": len(content) if content else 0})
        for target in wikilinks:
            edges.append({"source": name, "target": target})
    return {"nodes": nodes, "edges": edges}


@app.get("/nodes/{name}")
async def handle_node(name: str, request: Request) -> dict:
    ctx: GraphContext = request.app.state.ctx
    content = graph.read_node(ctx.graph_dir, name)
    if content is None:
        return {"error": f"Node '{name}' not found"}
    outlinks, backlinks = graph.get_links(ctx.graph_dir, name)
    return {"name": name, "content": content, "outlinks": outlinks, "backlinks": backlinks}
