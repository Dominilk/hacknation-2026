import re
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def read_node(graph_dir: Path, name: str) -> str | None:
    """Read node content. Returns None if not found."""
    path = graph_dir / f"{name}.md"
    if not path.exists():
        return None
    return path.read_text()


def write_node(graph_dir: Path, name: str, content: str) -> None:
    """Create/overwrite a node file."""
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / f"{name}.md").write_text(content)


def update_node(graph_dir: Path, name: str, content: str) -> bool:
    """Update existing node. Returns False if not found."""
    path = graph_dir / f"{name}.md"
    if not path.exists():
        return False
    path.write_text(content)
    return True


def list_nodes(graph_dir: Path) -> list[str]:
    """List all node names (stems of .md files)."""
    if not graph_dir.exists():
        return []
    return sorted(p.stem for p in graph_dir.glob("*.md"))


def extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilinks]] from content. Deduplicated, order-preserving."""
    seen = set()
    result = []
    for match in WIKILINK_RE.finditer(content):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def get_links(graph_dir: Path, name: str) -> tuple[list[str], list[str]]:
    """Return (outlinks, backlinks) for a node."""
    content = read_node(graph_dir, name)
    outlinks = extract_wikilinks(content) if content else []

    backlinks = []
    for node_name in list_nodes(graph_dir):
        if node_name == name:
            continue
        node_content = read_node(graph_dir, node_name)
        if node_content and f"[[{name}]]" in node_content:
            backlinks.append(node_name)
    return outlinks, backlinks


def search_nodes(graph_dir: Path, keyword: str) -> list[str]:
    """Case-insensitive substring search across all nodes. Returns matching node names."""
    keyword_lower = keyword.lower()
    results = []
    for name in list_nodes(graph_dir):
        content = read_node(graph_dir, name)
        if content and keyword_lower in content.lower():
            results.append(name)
    return results
