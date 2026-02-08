import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import Runner, set_default_openai_client
from shared import IngestEvent
from .context import GraphContext, Settings
from . import graph, embeddings
from .git_ops import init_repo, create_worktree, remove_worktree, commit, merge_worktree, git_log
from .agents.ingest import ingestion_agent, IngestionResult
from .agents.query import make_query_agent
from .tracing import TracingHooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    await init_repo(settings.graph_root)
    ctx = GraphContext.create(settings)
    set_default_openai_client(ctx.openai_client)
    app.state.ctx = ctx
    app.state.merge_lock = asyncio.Lock()
    yield


app = FastAPI(title="AI Chief of Staff", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class QueryRequest(BaseModel):
    question: str


async def ingest_event(ctx: GraphContext, event: IngestEvent, merge_lock: asyncio.Lock) -> dict:
    """Full ingestion orchestration: worktree -> event node -> agent -> commit -> merge -> cleanup.
    Returns combined IngestionResult + trace."""
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

        # Run ingestion agent with tracing
        tracing = TracingHooks()
        result = await Runner.run(
            ingestion_agent,
            input=f"Process event node: [[{event_name}]]",
            context=wt_ctx,
            hooks=tracing,
            max_turns=25,
        )
        output: IngestionResult = result.final_output

        # Commit in worktree
        await commit(worktree, output.commit_message)

        # Merge (serialized via lock)
        async with merge_lock:
            merge = await merge_worktree(ctx.graph_root, branch)

        # Re-embed changed files and update graph index after merge
        if merge.success:
            log = await git_log(ctx.graph_root, limit=1)
            if log and log[0]["files_changed"]:
                changed = log[0]["files_changed"]
                for f in changed:
                    if f.startswith("nodes/") and f.endswith(".md"):
                        node_name = Path(f).stem
                        content = graph.read_node(ctx.graph_dir, node_name)
                        if content:
                            await embeddings.embed_node(ctx, node_name, content)
                        else:
                            await embeddings.remove_embedding(ctx, node_name)
                if ctx.graph_index:
                    ctx.graph_index.update_from_changes(changed)

        return {**output.model_dump(), "trace": tracing.to_list()}
    finally:
        await remove_worktree(ctx.graph_root, worktree, branch)


@app.post("/ingest")
async def handle_ingest(event: IngestEvent, request: Request) -> dict:
    ctx: GraphContext = request.app.state.ctx
    merge_lock: asyncio.Lock = request.app.state.merge_lock
    return await ingest_event(ctx, event, merge_lock)


@app.post("/query")
async def handle_query(req: QueryRequest, request: Request) -> dict:
    ctx: GraphContext = request.app.state.ctx
    agent = make_query_agent(req.question)
    result = await Runner.run(agent, input=req.question, context=ctx, max_turns=15)
    return {"answer": result.final_output}


@app.get("/graph")
async def handle_graph(request: Request) -> dict:
    """Export graph for visualization: nodes + edges + analytics."""
    ctx: GraphContext = request.app.state.ctx
    assert ctx.graph_index is not None
    return ctx.graph_index.to_json()


@app.get("/graph/commits")
async def handle_graph_commits(request: Request, limit: int = 50) -> list[dict]:
    """Git log with files_changed per commit, for timeline slider."""
    ctx: GraphContext = request.app.state.ctx
    return await git_log(ctx.graph_root, limit=limit)


@app.get("/nodes/{name}")
async def handle_node(name: str, request: Request) -> dict:
    ctx: GraphContext = request.app.state.ctx
    content = graph.read_node(ctx.graph_dir, name)
    if content is None:
        return {"error": f"Node '{name}' not found"}
    if ctx.graph_index:
        outlinks = ctx.graph_index.get_outlinks(name)
        backlinks = ctx.graph_index.get_backlinks(name)
    else:
        outlinks, backlinks = graph.get_links(ctx.graph_dir, name)
    return {"name": name, "content": content, "outlinks": outlinks, "backlinks": backlinks}
