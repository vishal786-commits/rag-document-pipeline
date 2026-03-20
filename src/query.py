from src.embedder import embed_user_query
from src.vectorstore import search_in_pinecone
from src.llm import query_llm_with_context
"""
Process user queries by embedding them, searching for relevant context, and generating responses.
"""

def answer(query: str, namespace: str, chat_history: list):

    query_vector = embed_user_query(query)

    matched_chunks = search_in_pinecone(query_vector, namespace=namespace)
    
    context = "\n\n".join(matched_chunks)

    generated_response = query_llm_with_context(
        query,
        context,
        chat_history
    )
    return generated_response

if __name__ == "__main__":

    namespace = "test_namespace"
    chat_history = []

    print("Chat started. Type 'exit' to end.\n")

    while True:
        user_query = input("You: ")

        if user_query.lower() in ["exit", "quit", "q","end"]:
            print("Conversation ended.")
            break
        
        if not user_query.strip():
            continue

        response = answer(user_query, namespace, chat_history)

        chat_history.append((user_query, response))

        print("Assistant:", response)