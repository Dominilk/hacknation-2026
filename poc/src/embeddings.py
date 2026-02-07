from .context import GraphContext

EMBED_MODEL = "text-embedding-3-small"


def _format_content(name: str, content: str) -> str:
    return f"# {name}\n\n{content}"


async def _get_embedding(ctx: GraphContext, text: str) -> list[float]:
    resp = await ctx.openai_client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


async def embed_node(
    ctx: GraphContext, name: str, content: str, metadata: dict | None = None
) -> None:
    embedding = await _get_embedding(ctx, _format_content(name, content))
    meta = {}
    if metadata:
        if "type" in metadata:
            meta["type"] = metadata["type"]
        if "tags" in metadata:
            meta["tags"] = ",".join(metadata["tags"]) if isinstance(metadata["tags"], list) else metadata["tags"]
        if "updated" in metadata:
            meta["updated"] = metadata["updated"]
    ctx.collection.upsert(ids=[name], embeddings=[embedding], documents=[content], metadatas=[meta] if meta else None)


async def similarity_search(
    ctx: GraphContext, query: str, top_k: int = 5, where: dict | None = None
) -> list[dict]:
    embedding = await _get_embedding(ctx, query)
    kwargs: dict = dict(query_embeddings=[embedding], n_results=top_k, include=["documents", "distances"])
    if where:
        kwargs["where"] = where
    results = ctx.collection.query(**kwargs)

    if not results["ids"] or not results["ids"][0]:
        return []

    out = []
    for name, doc, dist in zip(results["ids"][0], results["documents"][0], results["distances"][0]):
        out.append({"name": name, "score": 1.0 - dist, "snippet": doc[:500]})
    return out


async def remove_node(ctx: GraphContext, name: str) -> None:
    ctx.collection.delete(ids=[name])


async def reindex_all(ctx: GraphContext, nodes: list[tuple[str, str, dict]]) -> None:
    if not nodes:
        return
    texts = [_format_content(name, content) for name, content, _ in nodes]
    # Batch embed all at once
    resp = await ctx.openai_client.embeddings.create(model=EMBED_MODEL, input=texts)
    embeddings = [item.embedding for item in resp.data]

    ids = []
    documents = []
    metadatas = []
    for (name, content, metadata), emb in zip(nodes, embeddings):
        ids.append(name)
        documents.append(content)
        meta = {}
        if "type" in metadata:
            meta["type"] = metadata["type"]
        if "tags" in metadata:
            meta["tags"] = ",".join(metadata["tags"]) if isinstance(metadata["tags"], list) else metadata["tags"]
        if "updated" in metadata:
            meta["updated"] = metadata["updated"]
        metadatas.append(meta)

    ctx.collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
