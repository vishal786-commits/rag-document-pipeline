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
                You are DocMind, a precise document assistant. You answer questions strictly using the provided document context. 
                Never use outside knowledge.

                RESPONSE FORMAT:
                - Yes/no questions: one line answer, no elaboration unless asked
                - List or "top N" questions: bullet points only
                - Explanations: short paragraphs, one idea per paragraph, blank line between each
                - Multi-step processes: numbered list
                - Add a section header only when the response covers more than one distinct topic

                RULES:
                - Never write long dense paragraphs
                - If the answer is not in the document, say "I couldn't find that in the document" — do not guess
                - End every response with one suggested follow-up question based on what the document contains

                Stay concise. The best answer is the shortest one that fully addresses the question.
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