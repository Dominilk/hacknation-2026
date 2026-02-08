from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from openai import AsyncOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    openai_api_key: str
    graph_root: Path = Path("graph")


@dataclass
class GraphContext:
    graph_dir: Path
    graph_root: Path
    chroma_collection: Collection
    openai_client: AsyncOpenAI

    @classmethod
    def create(cls, settings: Settings) -> "GraphContext":
        graph_root = settings.graph_root
        client = chromadb.PersistentClient(path=str(graph_root / "_index"))
        collection = client.get_or_create_collection("nodes", metadata={"hnsw:space": "cosine"})
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        return cls(
            graph_dir=graph_root / "nodes",
            graph_root=graph_root,
            chroma_collection=collection,
            openai_client=openai_client,
        )

    def for_worktree(self, worktree_path: Path) -> "GraphContext":
        """New context pointing at a worktree. Chromadb + OpenAI client are shared."""
        return GraphContext(
            graph_dir=worktree_path / "nodes",
            graph_root=worktree_path,
            chroma_collection=self.chroma_collection,
            openai_client=self.openai_client,
        )
