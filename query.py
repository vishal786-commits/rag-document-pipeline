from src.embedder import embed_user_query
from src.vectorstore import search_in_pinecone
from src.llm import query_llm_with_context
"""
Process user queries by embedding them, searching for relevant context, and generating responses.
"""

def answer(query: str):

    query_vector = embed_user_query(query)

    matched_chunks = search_in_pinecone(query_vector)

    generated_response = query_llm_with_context(query, matched_chunks)
    print(generated_response)

if __name__ == "__main__":
    user_query = input("Enter your query: ")
    answer(user_query)