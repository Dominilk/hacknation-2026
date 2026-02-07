"""Export the knowledge graph to JSON for visualization."""

import json
from pathlib import Path

from src.graph import get_links, list_nodes, read_node


def export_graph_json(graph_dir: Path) -> dict:
    """Export graph as {nodes: [...], links: [...]} for D3.js visualization."""
    node_names = list_nodes(graph_dir)

    nodes = []
    links = []
    seen_edges = set()

    for name in node_names:
        node = read_node(graph_dir, name)
        if node is None:
            continue
        nodes.append({
            "id": name,
            "type": node.node_type,
            "tags": node.tags,
            "content": node.content[:300],
            "updated": node.updated,
            "link_count": len(node.outlinks),
        })
        for target in node.outlinks:
            edge_key = (name, target)
            if edge_key not in seen_edges and target in node_names:
                seen_edges.add(edge_key)
                links.append({"source": name, "target": target})

    return {"nodes": nodes, "links": links}


if __name__ == "__main__":
    graph_dir = Path("graph/nodes")
    data = export_graph_json(graph_dir)
    out_path = Path("web/graph-data.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2))
    print(f"Exported {len(data['nodes'])} nodes, {len(data['links'])} links to {out_path}")
