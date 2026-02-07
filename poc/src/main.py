"""CLI for the AI Chief of Staff — knowledge graph with agentic ingestion."""

import asyncio
import json
import sys
from pathlib import Path

from agents import Runner

from src.agents.ingest import ingest_agent
from src.agents.query import query_agent
from src.context import GraphContext
from src.graph import get_links, list_nodes, read_node


def create_ctx(graph_root: str = "graph") -> GraphContext:
    return GraphContext.create(Path(graph_root))


async def cmd_ingest(ctx: GraphContext, text: str) -> None:
    """Ingest a single event into the knowledge graph."""
    print(f"Ingesting event ({len(text)} chars)...")
    result = await Runner.run(ingest_agent, input=text, context=ctx, max_turns=25)
    output = result.final_output
    print(f"\nResult:")
    print(f"  Created: {', '.join(output.nodes_created) or 'none'}")
    print(f"  Updated: {', '.join(output.nodes_updated) or 'none'}")
    print(f"  Summary: {output.summary}")


async def cmd_ingest_seeds(ctx: GraphContext, seeds_path: str = "seeds/events.json") -> None:
    """Ingest all seed events from a JSON file."""
    events = json.loads(Path(seeds_path).read_text())
    print(f"Ingesting {len(events)} seed events...\n")
    for i, event in enumerate(events, 1):
        header = f"[{event.get('type', 'unknown')}] {event.get('source', '')} ({event.get('timestamp', '')})"
        participants = ", ".join(event.get("participants", []))
        text = f"Event type: {event['type']}\nSource: {event.get('source', 'unknown')}\nTimestamp: {event.get('timestamp', '')}\nParticipants: {participants}\n\n{event['content']}"
        print(f"--- Event {i}/{len(events)}: {header} ---")
        try:
            await cmd_ingest(ctx, text)
        except Exception as e:
            print(f"  ERROR: {e}")
        print()


async def cmd_query(ctx: GraphContext, question: str, role: str = "general") -> None:
    """Query the knowledge graph."""
    prompt = f"[Perspective: {role}]\n\n{question}"
    print(f"Querying as {role}...")
    result = await Runner.run(query_agent, input=prompt, context=ctx)
    print(f"\n{result.final_output}")


async def cmd_graph_stats(ctx: GraphContext) -> None:
    """Show graph statistics."""
    nodes = list_nodes(ctx.graph_dir)
    total_links = 0
    orphans = []
    for name in nodes:
        outlinks, backlinks = get_links(ctx.graph_dir, name)
        total_links += len(outlinks)
        if not outlinks and not backlinks:
            orphans.append(name)

    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {total_links}")
    print(f"Orphans: {len(orphans)}")
    if orphans:
        print(f"  {', '.join(orphans)}")


async def cmd_graph_show(ctx: GraphContext, name: str) -> None:
    """Show a single node."""
    node = read_node(ctx.graph_dir, name)
    if node is None:
        print(f"Node '{name}' not found.")
        return
    outlinks, backlinks = get_links(ctx.graph_dir, name)
    print(f"=== {node.name} ({node.node_type}) ===")
    print(f"Tags: {', '.join(node.tags)}")
    print(f"Created: {node.created}")
    print(f"Updated: {node.updated}")
    print(f"Outlinks: {', '.join(f'[[{l}]]' for l in outlinks) or 'none'}")
    print(f"Backlinks: {', '.join(f'[[{l}]]' for l in backlinks) or 'none'}")
    print(f"\n{node.content}")


async def cmd_reindex(ctx: GraphContext) -> None:
    """Rebuild the embeddings index from all graph nodes."""
    from src.embeddings import reindex_all

    nodes_data = []
    for name in list_nodes(ctx.graph_dir):
        node = read_node(ctx.graph_dir, name)
        assert node is not None
        metadata = {"type": node.node_type, "tags": ",".join(node.tags), "updated": node.updated}
        nodes_data.append((name, node.content, metadata))
    print(f"Reindexing {len(nodes_data)} nodes...")
    await reindex_all(ctx, nodes_data)
    print("Done.")


USAGE = """\
Usage: uv run python -m src.main <command> [args]

Commands:
  ingest <text>              Ingest a single event
  ingest-seeds [path]        Ingest all events from seeds/events.json
  query <question> [--role <role>]  Query the graph (roles: ceo, engineer, pm, new-joiner)
  graph stats                Show graph statistics
  graph show <node>          Show a node with its links
  graph list                 List all nodes
  reindex                    Rebuild embeddings index
"""


async def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        return

    ctx = create_ctx()
    cmd = args[0]

    if cmd == "ingest" and len(args) > 1:
        await cmd_ingest(ctx, " ".join(args[1:]))
    elif cmd == "ingest-seeds":
        path = args[1] if len(args) > 1 else "seeds/events.json"
        await cmd_ingest_seeds(ctx, path)
    elif cmd == "query" and len(args) > 1:
        role = "general"
        question_parts = []
        i = 1
        while i < len(args):
            if args[i] == "--role" and i + 1 < len(args):
                role = args[i + 1]
                i += 2
            else:
                question_parts.append(args[i])
                i += 1
        await cmd_query(ctx, " ".join(question_parts), role)
    elif cmd == "graph" and len(args) > 1:
        subcmd = args[1]
        if subcmd == "stats":
            await cmd_graph_stats(ctx)
        elif subcmd == "show" and len(args) > 2:
            await cmd_graph_show(ctx, args[2])
        elif subcmd == "list":
            for name in list_nodes(ctx.graph_dir):
                print(f"  {name}")
        else:
            print(USAGE)
    elif cmd == "reindex":
        await cmd_reindex(ctx)
    else:
        print(USAGE)


if __name__ == "__main__":
    asyncio.run(main())
