from .context import GraphContext
from .graph import list_nodes, read_node

EMBED_MODEL = "text-embedding-3-small"


async def _get_embedding(ctx: GraphContext, text: str) -> list[float]:
    """Get embedding vector from OpenAI."""
    response = await ctx.openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def embed_node(ctx: GraphContext, name: str, content: str) -> None:
    """Embed node content and upsert to ChromaDB."""
    text = f"# {name}\n\n{content}"
    embedding = await _get_embedding(ctx, text)
    ctx.chroma_collection.upsert(
        ids=[name],
        documents=[content],
        embeddings=[embedding],
        metadatas=[{"name": name}],
    )


async def similarity_search(ctx: GraphContext, query: str, top_k: int = 5) -> list[dict]:
    """Cosine similarity search. Returns [{"name": str, "score": float, "snippet": str}, ...]"""
    if ctx.chroma_collection.count() == 0:
        return []

    query_embedding = await _get_embedding(ctx, query)
    results = ctx.chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, ctx.chroma_collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    out = []
    for id_, doc, dist in zip(
        results["ids"][0],
        results["documents"][0],
        results["distances"][0],
    ):
        out.append(
            {
                "name": id_,
                "score": 1.0 - dist,  # cosine distance → similarity
                "snippet": doc[:200] if doc else "",
            }
        )
    return out


async def remove_embedding(ctx: GraphContext, name: str) -> None:
    """Remove a node's embedding from ChromaDB."""
    ctx.chroma_collection.delete(ids=[name])


async def reindex_all(ctx: GraphContext) -> None:
    """Rebuild the entire index from nodes on disk."""
    existing = ctx.chroma_collection.get()
    if existing["ids"]:
        ctx.chroma_collection.delete(ids=existing["ids"])

    for name in list_nodes(ctx.graph_dir):
        content = read_node(ctx.graph_dir, name)
        if content:
            await embed_node(ctx, name, content)
