from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LLM_MODEL = "gpt-3.5-turbo"


def query_llm_with_context(query: str, context: str, chat_history: list) -> str:
    """
    Query the LLM using context + conversation history
    """

    try:

        messages = [
            {
                "role": "system",
                "content": 
                """
                You are a helpful assistant that answers questions using only the provided 
                document context. Format responses for readability by using short paragraphs 
                with a blank line after each, bullet points for lists, numbered lists for steps 
                or multiple questions, and clear section headers when helpful, while avoiding 
                long dense paragraphs. Maintain an engaging conversation and always end your 
                response with a suggested follow-up question based on the available context 
                to guide the user toward a deeper understanding of the material.

                answer yes or no question in one line.

                top-n things styles questions should be answered in bullet points.
                """
            }
        ]

        # Add conversation memory
        for q, a in chat_history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        # Add current query
        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion:\n{query}"
        })

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.4
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error querying LLM: {e}")
        return "Sorry, I couldn't process your request."