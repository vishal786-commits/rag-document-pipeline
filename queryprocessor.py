from embedder import embed_user_query
from vectorstore import search_in_pinecone
from llm import query_llm_with_context
"""
Process user queries by embedding them, searching for relevant context, and generating responses.
"""

def process_user_query(query: str):

    query_vector = embed_user_query(query)

    matched_chunks = search_in_pinecone(query_vector)

    generated_response = query_llm_with_context(query, matched_chunks)
    print(generated_response)

if __name__ == "__main__":
    user_query = input("Enter your query: ")
    # user_query = "Is homosexuality bad according to marie louise von franz?"
    process_user_query(user_query)