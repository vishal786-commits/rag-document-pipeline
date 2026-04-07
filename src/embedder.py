from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import List
import asyncio

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = "text-embedding-3-small"

async def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text chunks using OpenAI's embedding model.
    
    Args:
        chunks (List[str]): List of text chunks to embed.
    """
    embeddings = []
    for chunk in chunks:
        try:
            response = await asyncio.to_thread(
                client.embeddings.create,
                input=chunk,
                model=EMBEDDING_MODEL
            )
            embedding = response.data[0].embedding
            embeddings.append(embedding)
        except Exception as e:
            print(f"Error embedding chunk: {e}")
            embeddings.append([])  # Append an empty embedding for failed chunks    
    return embeddings

async def embed_user_query(query: str) -> List[float]:
    """
    Generate an embedding for a user query.
    
    Args:
        query (str): The user query to embed.
    
    Returns:
        List[float]: The embedding for the user query.
    """
    try:
        response = await asyncio.to_thread(
            client.embeddings.create,
            input=query,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error embedding user query: {e}")
        return []  # Return an empty embedding for failed queries