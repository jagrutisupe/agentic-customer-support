from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from app.rag.loader import load_and_chunk_documents


# Store the vector database inside the project
VECTOR_DB_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "chroma_db"
)

VECTOR_DB_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# Local embedding model
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)


# ChromaDB persistent client
chroma_client = chromadb.PersistentClient(
    path=str(VECTOR_DB_DIR)
)


# Collection for customer-support knowledge
collection = chroma_client.get_or_create_collection(
    name="customer_support_knowledge"
)


def build_vector_store():
    """
    Load knowledge-base documents, create embeddings,
    and store the chunks in ChromaDB.
    """

    chunks = load_and_chunk_documents()

    if not chunks:
        print("No knowledge-base documents found.")
        return

    documents = [
        chunk["content"]
        for chunk in chunks
    ]

    ids = [
        f'{chunk["filename"]}_{chunk["chunk_id"]}'
        for chunk in chunks
    ]

    metadatas = [
        {
            "filename": chunk["filename"],
            "chunk_id": chunk["chunk_id"],
        }
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(
        documents,
        show_progress_bar=True,
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print("=" * 50)
    print("Vector store built successfully!")
    print(f"Documents/chunks: {len(documents)}")
    print(f"Collection: {collection.name}")
    print(f"Database: {VECTOR_DB_DIR}")
    print("=" * 50)


def search_knowledge(
    query: str,
    top_k: int = 3,
):
    """
    Search the knowledge base using semantic similarity.
    """

    query_embedding = embedding_model.encode(
        [query]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )

    return results