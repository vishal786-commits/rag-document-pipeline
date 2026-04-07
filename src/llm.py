from openai import OpenAI
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LLM_MODEL = "gpt-3.5-turbo"


async def rewrite_query(query: str) -> str:
    """
    Rewrite the user query to fix spelling, grammar, and clarity
    before embedding. Better query = better retrieval.
    """
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a query rewriting assistant. "
                        "Fix spelling mistakes and grammar errors only. "
                        "If the query is already clear and correct, return it unchanged. "
                        "Keep the meaning identical — do not add information or change what is being asked. "
                        "Return only the rewritten question, nothing else. No explanation, no preamble."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[rewrite_query] Error: {e}, falling back to original query")
        return query  # fallback — never let a rewrite failure break the whole pipeline


async def query_llm_with_context(query: str, context: str, chat_history: list) -> str:
    """
    Query the LLM using context + conversation history.
    """
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are DocMind, a precise document assistant. You answer questions strictly using the provided document context. "
                    "Never use outside knowledge.\n\n"
                    "RESPONSE FORMAT:\n"
                    "- Yes/no questions: start with a clear Yes or No, then 1-2 sentences explaining why using the most relevant policy content. "
                    "If not explicitly stated, infer from related clauses and begin your reasoning with 'Based on the policy...'\n"
                    "- List and 'top N' questions: bullet points only\n"
                    "- Summary requests: bullet points, one key point per bullet, maximum 8 bullets\n"
                    "- Explanations: short paragraphs, one idea per paragraph, blank line between each\n"
                    "- Multi-step processes: numbered list\n"
                    "- Add a section header only when the response covers more than one distinct topic\n\n"
                    "RULES:\n"
                    "- Never write long dense paragraphs\n"
                    "- Never invent facts or use outside knowledge\n"
                    "- If the answer is genuinely not inferable from the document, say 'The document does not cover this topic'\n"
                    "- End every response with one suggested follow-up question based on what the document contains\n\n"
                    "Stay concise. The best answer is the shortest one that fully addresses the question."
                )
            }
        ]

        # Add conversation memory
        for q, a in chat_history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        # Add current query with context
        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion:\n{query}"
        })

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=LLM_MODEL,
            messages=messages,
            temperature=0.5
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[query_llm] Error: {e}")
        return "Sorry, I couldn't process your request."