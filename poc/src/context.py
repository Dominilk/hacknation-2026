from dataclasses import dataclass
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


@dataclass
class GraphContext:
    graph_dir: Path
    chroma_client: chromadb.ClientAPI
    collection: chromadb.Collection
    openai_client: AsyncOpenAI

    @classmethod
    def create(cls, graph_root: Path | str = "graph") -> "GraphContext":
        graph_root = Path(graph_root)
        graph_root.mkdir(parents=True, exist_ok=True)
        (graph_root / "nodes").mkdir(exist_ok=True)

        chroma_client = chromadb.PersistentClient(path=str(graph_root / "_index"))
        collection = chroma_client.get_or_create_collection(
            name="knowledge_graph",
            metadata={"hnsw:space": "cosine"},
        )

        return cls(
            graph_dir=graph_root / "nodes",
            chroma_client=chroma_client,
            collection=collection,
            openai_client=AsyncOpenAI(),
        )
