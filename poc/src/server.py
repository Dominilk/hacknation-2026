"""FastAPI backend for the AI Chief of Staff visualization."""

from contextlib import asynccontextmanager
from pathlib import Path

from agents import Runner
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agents.ingest import ingest_agent
from src.agents.query import query_agent
from src.context import GraphContext
from src.export_graph import export_graph_json
from src.graph import get_links, list_nodes, read_node

ctx: GraphContext


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ctx
    ctx = GraphContext.create(Path("graph"))
    yield


app = FastAPI(lifespan=lifespan)


class IngestRequest(BaseModel):
    content: str
    event_type: str = "unknown"
    source: str = ""
    participants: list[str] = []


class QueryRequest(BaseModel):
    question: str
    role: str = "general"


@app.get("/api/graph")
async def api_graph():
    return export_graph_json(ctx.graph_dir)


@app.post("/api/ingest")
async def api_ingest(req: IngestRequest):
    parts = [f"Event type: {req.event_type}", f"Source: {req.source}"]
    if req.participants:
        parts.append(f"Participants: {', '.join(req.participants)}")
    text = "\n".join(parts) + f"\n\n{req.content}"
    result = await Runner.run(ingest_agent, input=text, context=ctx, max_turns=25)
    output = result.final_output
    return {
        "nodes_created": output.nodes_created,
        "nodes_updated": output.nodes_updated,
        "summary": output.summary,
        "graph": export_graph_json(ctx.graph_dir),
    }


@app.post("/api/query")
async def api_query(req: QueryRequest):
    prompt = f"[Perspective: {req.role}]\n\n{req.question}"
    result = await Runner.run(query_agent, input=prompt, context=ctx, max_turns=25)
    return {"answer": result.final_output}


@app.get("/api/node/{name}")
async def api_node(name: str):
    node = read_node(ctx.graph_dir, name)
    if node is None:
        return {"error": "not found"}
    outlinks, backlinks = get_links(ctx.graph_dir, name)
    return {
        "name": node.name,
        "type": node.node_type,
        "tags": node.tags,
        "content": node.content,
        "created": node.created,
        "updated": node.updated,
        "outlinks": outlinks,
        "backlinks": backlinks,
    }


@app.get("/api/stats")
async def api_stats():
    names = list_nodes(ctx.graph_dir)
    type_counts: dict[str, int] = {}
    for name in names:
        node = read_node(ctx.graph_dir, name)
        if node:
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1
    graph = export_graph_json(ctx.graph_dir)
    return {
        "nodes": len(graph["nodes"]),
        "edges": len(graph["links"]),
        "types": type_counts,
    }


app.mount("/", StaticFiles(directory="web", html=True))
