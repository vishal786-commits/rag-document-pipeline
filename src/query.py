from src.embedder import embed_user_query
from src.vectorstore import search_in_pinecone
from src.llm import query_llm_with_context, rewrite_query
from rank_bm25 import BM25Okapi


def rerank_with_bm25(query: str, chunks: list[str], top_k: int = 5) -> list[str]:
    """
    Rerank retrieved chunks using BM25 keyword scoring.
    Pinecone gives us candidates by meaning, BM25 then scores by keyword match.
    We return the top_k chunks after reranking.
    """
    # BM25 expects tokenised input — split each chunk into words
    tokenised_chunks = [chunk.lower().split() for chunk in chunks]
    tokenised_query = query.lower().split()

    bm25 = BM25Okapi(tokenised_chunks)
    scores = bm25.get_scores(tokenised_query)

    # Pair each chunk with its BM25 score and sort descending
    scored_chunks = sorted(zip(scores, chunks), reverse=True)

    # Return just the text of the top_k chunks
    return [chunk for _, chunk in scored_chunks[:top_k]]


async def answer(query: str, namespace: str, chat_history: list, chunk_count: int = 20) -> str:

    # Scale retrieval to document size
    # Small doc (< 30 chunks): retrieve everything, rerank keeps 80%
    # Medium doc (30-100 chunks): retrieve 30, rerank keeps top 8
    # Large doc (> 100 chunks): retrieve 20, rerank keeps top 5
    if chunk_count < 30:
        retrieve_k = chunk_count  # just get everything
        rerank_k = max(5, chunk_count // 2)
    elif chunk_count < 100:
        retrieve_k = 30
        rerank_k = 8
    else:
        retrieve_k = 20
        rerank_k = 5

    rewritten_query = await rewrite_query(query)
    query_vector = await embed_user_query(rewritten_query)
    matched_chunks = await search_in_pinecone(query_vector, top_k=retrieve_k, namespace=namespace)
    reranked_chunks = rerank_with_bm25(rewritten_query, matched_chunks, top_k=rerank_k)
    context = "\n\n".join(reranked_chunks)
    return await query_llm_with_context(query, context, chat_history)