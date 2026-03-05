from pinecone import Pinecone
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

PINECONE_CLIENT = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX = PINECONE_CLIENT.Index(os.getenv("PINECONE_INDEX_NAME"))

def store_in_pinecone(chunks: List[str], embeddings: List[List[float]], namespace: str =""):
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
        
        index = INDEX
        
        # Prepare data for upsert
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_data = {
                "id": f"chunk_{i}",  # Unique ID for each chunk
                "values": embedding,  # The embedding vector
                "metadata": {"text": chunk,
                             "chunk_index": i}  # Store the original text as metadata
            }
            vectors.append(vector_data)

        
        # Upsert vectors into Pinecone
        batch_size = 100  # Adjust batch size as needed
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            
            index.upsert(
                vectors=batch,
                namespace=namespace
            )
            
            # print(f"Uploaded batch {i//batch_size + 1}")
        print(f"Successfully stored {len(chunks)} chunks in Pinecone under namespace '{namespace}'.")
    except Exception as e:
        print(f"Error storing in Pinecone: {e}")

def search_in_pinecone(query_embedding: List[float], top_k: int = 10, namespace: str ="") -> List[dict]:
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
        index = INDEX
        response = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace
        )
        
        matched_chunks = []
        for match in response.matches:
            result = match.metadata.get("text", "")
            matched_chunks.append(result)
        
        return matched_chunks
    except Exception as e:
        print(f"Error searching in Pinecone: {e}")
        return []