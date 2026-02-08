from __future__ import annotations

from pathlib import Path

import networkx as nx

from .graph import extract_wikilinks, list_nodes, read_node


class GraphIndex:
    """In-memory DiGraph index over the knowledge graph's wikilinks.

    Provides O(1) link lookups and on-demand analytics (PageRank, communities, centrality).
    """

    def __init__(self, graph_dir: Path):
        self.G = nx.DiGraph()
        self.graph_dir = graph_dir
        self._analytics_cache: dict | None = None

    def build(self) -> None:
        """Full rebuild from disk. Called once at startup."""
        self.G.clear()
        self._analytics_cache = None
        for name in list_nodes(self.graph_dir):
            content = read_node(self.graph_dir, name)
            self.G.add_node(name)
            if content:
                for target in extract_wikilinks(content):
                    self.G.add_edge(name, target)

    def update_node(self, name: str, content: str | None) -> None:
        """Update a single node's edges. content=None means deleted."""
        self._analytics_cache = None
        # Remove all outgoing edges
        if self.G.has_node(name):
            self.G.remove_edges_from(list(self.G.out_edges(name)))
        if content is None:
            if self.G.has_node(name):
                self.G.remove_node(name)
            return
        self.G.add_node(name)
        for target in extract_wikilinks(content):
            self.G.add_edge(name, target)

    def update_from_changes(self, changed_files: list[str]) -> None:
        """After merge, re-scan only changed nodes. Files are like 'nodes/foo.md'."""
        for f in changed_files:
            if not (f.startswith("nodes/") and f.endswith(".md")):
                continue
            name = Path(f).stem
            content = read_node(self.graph_dir, name)
            self.update_node(name, content)

    def get_outlinks(self, name: str) -> list[str]:
        if not self.G.has_node(name):
            return []
        return list(self.G.successors(name))

    def get_backlinks(self, name: str) -> list[str]:
        if not self.G.has_node(name):
            return []
        return list(self.G.predecessors(name))

    def get_analytics(self) -> dict:
        """PageRank, Louvain communities, betweenness centrality. Cached until next mutation."""
        if self._analytics_cache is not None:
            return self._analytics_cache

        if self.G.number_of_nodes() == 0:
            self._analytics_cache = {"pagerank": {}, "communities": {}, "centrality": {}}
            return self._analytics_cache

        pagerank = nx.pagerank(self.G)

        # Louvain needs undirected graph
        undirected = self.G.to_undirected()
        communities: dict[str, int] = {}
        if undirected.number_of_edges() > 0:
            partition = nx.community.louvain_communities(undirected)
            for i, community in enumerate(partition):
                for node in community:
                    communities[node] = i
        else:
            for node in self.G.nodes:
                communities[node] = 0

        centrality = nx.betweenness_centrality(self.G)

        self._analytics_cache = {
            "pagerank": pagerank,
            "communities": communities,
            "centrality": centrality,
        }
        return self._analytics_cache

    def to_json(self) -> dict:
        """Export for frontend viz. Includes analytics as node attributes."""
        analytics = self.get_analytics()
        nodes = []
        for name in self.G.nodes:
            nodes.append(
                {
                    "name": name,
                    "pagerank": analytics["pagerank"].get(name, 0),
                    "community": analytics["communities"].get(name, 0),
                    "centrality": analytics["centrality"].get(name, 0),
                }
            )
        edges = [{"source": u, "target": v} for u, v in self.G.edges]
        return {"nodes": nodes, "edges": edges}
