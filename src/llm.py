from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LLM_MODEL = "gpt-3.5-turbo"

def query_llm_with_context(query: str, context: str) -> str:
    """
    Query the LLM with the user query and retrieved context.
    
    Args:
        query (str): The user query.
        context (str): The retrieved context to provide to the LLM.
    
    Returns:
        str: The response from the LLM.
    """
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant helping answer questions about the book The Problem of the Puer Aeternus and related Jungian psychology concepts. You will be provided with passages retrieved from the book as context. Use only the information in the provided context to answer the user’s question clearly and concisely. Do not invent information or rely on outside knowledge. If the answer cannot be found in the context, respond by saying that the information is not available in the provided material. Focus on explaining ideas accurately and in simple language while staying faithful to the meaning of the original text."},
                {"role": "user", "content": f"Context: {context}\n\nQuery: {query}"}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return "Sorry, I couldn't process your request at this time."