"""Agent tools — wraps graph + embeddings as @function_tool for OpenAI Agents SDK."""

from typing import Annotated

from agents import RunContextWrapper, function_tool

from src.context import GraphContext
from src.embeddings import embed_node, remove_node, similarity_search
from src.graph import get_links, list_nodes, read_node, search_nodes, update_node, write_node


@function_tool
async def tool_similarity_search(
    ctx: RunContextWrapper[GraphContext],
    query: Annotated[str, "Search query to find relevant knowledge nodes"],
    top_k: Annotated[int, "Number of results to return"] = 5,
) -> str:
    """Search the knowledge graph for nodes semantically similar to the query."""
    results = await similarity_search(ctx.context, query, top_k=top_k)
    if not results:
        return "No matching nodes found."
    lines = []
    for r in results:
        lines.append(f"- **{r['name']}** (score: {r['score']:.3f}): {r['snippet'][:200]}")
    return "\n".join(lines)


@function_tool
async def tool_read_node(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Name of the node to read (e.g. 'auth-migration')"],
) -> str:
    """Read the full content of a knowledge node, including its metadata and wikilinks."""
    node = read_node(ctx.context.graph_dir, name)
    if node is None:
        return f"Node '{name}' not found."
    links_str = ", ".join(f"[[{l}]]" for l in node.outlinks) if node.outlinks else "none"
    return (
        f"**{node.name}** (type: {node.node_type})\n"
        f"Tags: {', '.join(node.tags)}\n"
        f"Links: {links_str}\n"
        f"Updated: {node.updated}\n\n"
        f"{node.content}"
    )


@function_tool
async def tool_list_links(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Name of the node to get links for"],
) -> str:
    """Get outgoing and incoming links for a knowledge node."""
    outlinks, backlinks = get_links(ctx.context.graph_dir, name)
    out_str = ", ".join(f"[[{l}]]" for l in outlinks) if outlinks else "none"
    back_str = ", ".join(f"[[{l}]]" for l in backlinks) if backlinks else "none"
    return f"Outlinks: {out_str}\nBacklinks: {back_str}"


@function_tool
async def tool_create_node(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Kebab-case name for the new node (e.g. 'auth-migration')"],
    node_type: Annotated[str, "Type: person, project, topic, decision, insight, goal, or team"],
    content: Annotated[str, "Markdown content for the node. Use [[wikilinks]] to reference other nodes."],
    tags: Annotated[str, "Comma-separated tags (e.g. 'engineering,backend')"] = "",
) -> str:
    """Create a new knowledge node in the graph."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    node = write_node(ctx.context.graph_dir, name, node_type, content, tags=tag_list)
    # Embed the new node
    metadata = {"type": node.node_type, "tags": ",".join(node.tags), "updated": node.updated}
    await embed_node(ctx.context, name, content, metadata=metadata)
    return f"Created node '{name}' (type: {node_type})"


@function_tool
async def tool_update_node(
    ctx: RunContextWrapper[GraphContext],
    name: Annotated[str, "Name of the node to update"],
    new_content: Annotated[str, "New markdown content (replaces existing). Use [[wikilinks]]."],
) -> str:
    """Update the content of an existing knowledge node."""
    node = update_node(ctx.context.graph_dir, name, new_content)
    if node is None:
        return f"Node '{name}' not found."
    metadata = {"type": node.node_type, "tags": ",".join(node.tags), "updated": node.updated}
    await embed_node(ctx.context, name, new_content, metadata=metadata)
    return f"Updated node '{name}'"


@function_tool
async def tool_search_nodes(
    ctx: RunContextWrapper[GraphContext],
    keyword: Annotated[str, "Keyword to search for across all nodes"],
) -> str:
    """Full-text keyword search across all knowledge nodes."""
    matches = search_nodes(ctx.context.graph_dir, keyword)
    if not matches:
        return f"No nodes contain '{keyword}'."
    return f"Nodes matching '{keyword}': {', '.join(matches)}"


# Tool sets for different agent roles
READ_TOOLS = [tool_similarity_search, tool_read_node, tool_list_links, tool_search_nodes]
WRITE_TOOLS = [tool_create_node, tool_update_node]
ALL_TOOLS = READ_TOOLS + WRITE_TOOLS
