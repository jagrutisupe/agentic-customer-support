from app.rag.vector_store import (
    build_vector_store,
    search_knowledge,
)


if __name__ == "__main__":
    build_vector_store()

    print("\nTesting semantic search...\n")

    queries = [
        "Can I return a product?",
        "How long does delivery take?",
        "What is the warranty period?",
        "My order was cancelled. What should I do?",
    ]

    for query in queries:
        print("=" * 60)
        print("QUERY:", query)

        results = search_knowledge(
            query,
            top_k=2,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for i, document in enumerate(documents):
            print(f"\nResult {i + 1}")
            print("File:", metadatas[i]["filename"])
            print("Content:")
            print(document[:500])