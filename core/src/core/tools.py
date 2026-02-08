from typing import Annotated

from agents import RunContextWrapper, function_tool

from .context import GraphContext
from . import graph, embeddings
from .git_ops import git_log


# --- READ tools ---


@function_tool
async def tool_similarity_search(
    ctx: RunContextWrapper[GraphContext],
    query: Annotated[str, "Natural language search query"],
    top_k: Annotated[int, "Number of results (default 5)"] = 5,
) -> str:
    """Search the knowledge graph for nodes similar to the query."""
    results = await embeddings.similarity_search(ctx.context, query, top_k)
    if not results:
        return "No similar nodes found."
    lines = [f"- [[{r['name']}]] (score: {r['score']:.2f}): {r['snippet'][:100]}..." for r in results]
    return "Similar nodes:\n" + "\n".join(lines)


@function_tool
async def tool_read_node(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Node name (kebab-case)"],
) -> str:
    """Read a knowledge node's full content with its links."""
    content = graph.read_node(ctx.context.graph_dir, name)
    if content is None:
        return f"Node '{name}' does not exist."
    outlinks, backlinks = graph.get_links(ctx.context.graph_dir, name)
    out_str = ", ".join(f"[[{link}]]" for link in outlinks) or "none"
    back_str = ", ".join(f"[[{link}]]" for link in backlinks) or "none"
    return f"{content}\n\n---\nOutlinks: {out_str}\nBacklinks: {back_str}"


@function_tool
async def tool_list_links(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Node name (kebab-case)"],
) -> str:
    """List a node's outgoing and incoming wikilinks."""
    outlinks, backlinks = graph.get_links(ctx.context.graph_dir, name)
    out_str = ", ".join(f"[[{link}]]" for link in outlinks) or "none"
    back_str = ", ".join(f"[[{link}]]" for link in backlinks) or "none"
    return f"Outlinks: {out_str}\nBacklinks: {back_str}"


@function_tool
async def tool_search_nodes(
    ctx: RunContextWrapper[GraphContext],
    keyword: Annotated[str, "Keyword to search for (case-insensitive)"],
) -> str:
    """Full-text keyword search across all nodes."""
    results = graph.search_nodes(ctx.context.graph_dir, keyword)
    if not results:
        return f"No nodes contain '{keyword}'."
    return "Matching nodes:\n" + "\n".join(f"- [[{n}]]" for n in results)


@function_tool
async def tool_get_recent_changes(
    ctx: RunContextWrapper[GraphContext],
    since: Annotated[str, "ISO date string, e.g. '2026-02-07' (optional)"] = "",
) -> str:
    """Get recent changes from git history."""
    entries = await git_log(ctx.context.graph_root, since=since or None)
    if not entries:
        return "No recent changes found."
    lines = []
    for e in entries[:10]:
        files = ", ".join(e["files_changed"][:5]) if e["files_changed"] else "no files"
        lines.append(f"- [{e['timestamp']}] {e['message']} ({files})")
    return "Recent changes:\n" + "\n".join(lines)


# --- WRITE tools (ingestion agent only) ---


@function_tool
async def tool_create_node(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Node name in kebab-case (e.g. 'auth-migration', 'alice-chen')"],
    content: Annotated[str, "Full markdown content with [[wikilinks]]"],
) -> str:
    """Create a new knowledge node. Fails if node already exists."""
    if graph.read_node(ctx.context.graph_dir, name) is not None:
        return f"Node '{name}' already exists. Use update_node instead."
    graph.write_node(ctx.context.graph_dir, name, content)
    await embeddings.embed_node(ctx.context, name, content)
    return f"Created [[{name}]]."


@function_tool
async def tool_update_node(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Node name (kebab-case)"],
    content: Annotated[str, "Complete replacement content (read existing content first!)"],
) -> str:
    """Update an existing node. Content is a FULL REPLACEMENT — read the node first, then provide complete updated content."""
    if not graph.update_node(ctx.context.graph_dir, name, content):
        return f"Node '{name}' does not exist. Use create_node instead."
    await embeddings.embed_node(ctx.context, name, content)
    return f"Updated [[{name}]]."


READ_TOOLS = [tool_similarity_search, tool_read_node, tool_list_links, tool_search_nodes, tool_get_recent_changes]
WRITE_TOOLS = [tool_create_node, tool_update_node]
ALL_TOOLS = READ_TOOLS + WRITE_TOOLS
