import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass
class NodeData:
    name: str
    node_type: str
    content: str
    tags: list[str] = field(default_factory=list)
    created: str = ""
    updated: str = ""
    outlinks: list[str] = field(default_factory=list)


def _node_path(graph_dir: Path, name: str) -> Path:
    return graph_dir / f"{name}.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _extract_wikilinks(text: str) -> list[str]:
    return list(dict.fromkeys(WIKILINK_RE.findall(text)))


def _parse_node(path: Path) -> NodeData | None:
    if not path.is_file():
        return None
    raw = path.read_text()
    name = path.stem

    # Split frontmatter from content
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()
        else:
            meta, content = {}, raw
    else:
        meta, content = {}, raw

    return NodeData(
        name=name,
        node_type=meta.get("type", ""),
        content=content,
        tags=meta.get("tags", []) or [],
        created=str(meta.get("created", "")),
        updated=str(meta.get("updated", "")),
        outlinks=_extract_wikilinks(content),
    )


def read_node(graph_dir: Path, name: str) -> NodeData | None:
    return _parse_node(_node_path(graph_dir, name))


def write_node(
    graph_dir: Path,
    name: str,
    node_type: str,
    content: str,
    tags: list[str] | None = None,
) -> NodeData:
    now = _now_iso()
    meta = {
        "type": node_type,
        "created": now,
        "updated": now,
        "tags": tags or [],
    }
    frontmatter = yaml.dump(meta, default_flow_style=None, sort_keys=False).strip()
    text = f"---\n{frontmatter}\n---\n\n{content}\n"
    _node_path(graph_dir, name).write_text(text)

    return NodeData(
        name=name,
        node_type=node_type,
        content=content,
        tags=tags or [],
        created=now,
        updated=now,
        outlinks=_extract_wikilinks(content),
    )


def update_node(graph_dir: Path, name: str, content: str) -> NodeData | None:
    existing = read_node(graph_dir, name)
    if existing is None:
        return None
    now = _now_iso()
    meta = {
        "type": existing.node_type,
        "created": existing.created,
        "updated": now,
        "tags": existing.tags,
    }
    frontmatter = yaml.dump(meta, default_flow_style=None, sort_keys=False).strip()
    text = f"---\n{frontmatter}\n---\n\n{content}\n"
    _node_path(graph_dir, name).write_text(text)

    return NodeData(
        name=name,
        node_type=existing.node_type,
        content=content,
        tags=existing.tags,
        created=existing.created,
        updated=now,
        outlinks=_extract_wikilinks(content),
    )


def list_nodes(graph_dir: Path) -> list[str]:
    return [p.stem for p in sorted(graph_dir.glob("*.md"))]


def get_links(graph_dir: Path, name: str) -> tuple[list[str], list[str]]:
    node = read_node(graph_dir, name)
    outlinks = node.outlinks if node else []

    backlinks = []
    for path in graph_dir.glob("*.md"):
        if path.stem == name:
            continue
        other = _parse_node(path)
        if other and name in other.outlinks:
            backlinks.append(other.name)

    return outlinks, backlinks


def search_nodes(graph_dir: Path, keyword: str) -> list[str]:
    keyword_lower = keyword.lower()
    matches = []
    for path in graph_dir.glob("*.md"):
        if keyword_lower in path.read_text().lower():
            matches.append(path.stem)
    return matches
