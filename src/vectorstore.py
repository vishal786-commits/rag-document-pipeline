from pinecone import Pinecone
import os
from dotenv import load_dotenv
from typing import List
import asyncio

load_dotenv()

_client = None
_index = None

def get_index():
    global _client, _index
    if _index is None:
        _client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        _index = _client.Index(os.getenv("PINECONE_INDEX_NAME"))
    return _index


async def store_in_pinecone(chunks: List[str], embeddings: List[List[float]], namespace: str = ""):
    """
    Store the text chunks and their corresponding embeddings in Pinecone.

    Args:
        chunks (List[str]): List of text chunks.
        embeddings (List[List[float]]): List of corresponding embeddings for the chunks.
        namespace (str): Namespace to store the vectors in Pinecone.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("The number of chunks and embeddings must be the same.")

    try:
        index = get_index()

        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vectors.append({
                "id": f"chunk_{i}",
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "chunk_index": i
                }
            })

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            await asyncio.to_thread(index.upsert, vectors=batch, namespace=namespace)

        print(f"Successfully stored {len(chunks)} chunks in Pinecone under namespace '{namespace}'.")

    except Exception as e:
        print(f"Error storing in Pinecone: {e}")


async def search_in_pinecone(query_embedding: List[float], top_k: int = 10, namespace: str = "") -> List[dict]:
    """
    Search for similar chunks in Pinecone based on a query embedding.

    Args:
        query_embedding (List[float]): The embedding of the user query.
        top_k (int): The number of top results to return.
        namespace (str): Namespace to search within Pinecone.

    Returns:
        List[dict]: A list of search results with metadata and similarity scores.
    """
    try:
        index = get_index()
        response = await asyncio.to_thread(
            index.query,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace
        )

        return [match.metadata.get("text", "") for match in response.matches]

    except Exception as e:
        print(f"Error searching in Pinecone: {e}")
        return []