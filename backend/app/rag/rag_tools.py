from app.rag.vector_store import search_knowledge


def search_knowledge_base(
    query: str,
    top_k: int = 5,
):
    """
    Search the customer-support knowledge base
    using semantic similarity.

    Returns unique retrieved chunks with metadata.
    Relevance filtering and final answer construction
    are handled by the agent router.
    """

    results = search_knowledge(
        query=query,
        top_k=top_k,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    matches = []
    seen_content = set()

    for i, document in enumerate(documents):

        if not document:
            continue

        document = document.strip()

        if not document:
            continue

        # Normalize whitespace for duplicate detection
        normalized_content = " ".join(
            document.split()
        ).strip()

        if normalized_content in seen_content:
            continue

        seen_content.add(normalized_content)

        metadata = (
            metadatas[i]
            if i < len(metadatas)
            else {}
        )

        distance = (
            distances[i]
            if i < len(distances)
            else None
        )

        matches.append(
            {
                "content": document,
                "filename": metadata.get(
                    "filename",
                    "unknown",
                ),
                "chunk_id": metadata.get(
                    "chunk_id",
                    i,
                ),
                "distance": distance,
            }
        )

    return {
        "success": True,
        "query": query,
        "count": len(matches),
        "results": matches,
    }