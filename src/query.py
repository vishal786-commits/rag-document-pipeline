from src.embedder import embed_user_query
from src.vectorstore import search_in_pinecone
from src.llm import query_llm_with_context, rewrite_query
from src.corpus_store import get_corpus
from src.hybrid import bm25_rank, reciprocal_rank_fusion
from rank_bm25 import BM25Okapi


def rerank_with_bm25(query: str, chunks: list[str], top_k: int = 5) -> list[str]:
    """
    Rerank an already-retrieved set of chunks using BM25 keyword scoring.
    Used as the fallback path when the full corpus isn't available for true
    hybrid fusion (e.g. a namespace ingested before this process started).
    """
    if not chunks:
        return []
    tokenised_chunks = [chunk.lower().split() for chunk in chunks]
    tokenised_query = query.lower().split()

    bm25 = BM25Okapi(tokenised_chunks)
    scores = bm25.get_scores(tokenised_query)

    scored_chunks = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored_chunks[:top_k]]


def _retrieval_sizes(chunk_count: int) -> tuple[int, int]:
    """
    Scale retrieval depth to document size.
      Small  (< 30 chunks) : consider everything, keep ~half
      Medium (30-100)      : consider 30, keep 8
      Large  (> 100)       : consider 20, keep 5
    Returns (candidate_k, final_k).
    """
    if chunk_count < 30:
        return chunk_count, max(5, chunk_count // 2)
    elif chunk_count < 100:
        return 30, 8
    return 20, 5


async def answer(query: str, namespace: str, chat_history: list, chunk_count: int = 20) -> str:
    candidate_k, final_k = _retrieval_sizes(chunk_count)

    rewritten_query = await rewrite_query(query)
    query_vector = await embed_user_query(rewritten_query)

    # Dense ranking from Pinecone (semantic).
    dense_ranked = await search_in_pinecone(query_vector, top_k=candidate_k, namespace=namespace)

    # Sparse ranking from BM25 over the FULL corpus (keyword). This can surface exact-term
    # matches that dense retrieval dropped, because BM25 sees every chunk — not just dense's.
    corpus = get_corpus(namespace)

    if corpus:
        sparse_ranked = bm25_rank(rewritten_query, corpus)[:candidate_k]
        # Fuse the two independent rankings with Reciprocal Rank Fusion.
        reranked_chunks = reciprocal_rank_fusion([dense_ranked, sparse_ranked], top_k=final_k)
    else:
        # Fallback: corpus unavailable — rerank the dense candidates only (legacy path).
        reranked_chunks = rerank_with_bm25(rewritten_query, dense_ranked, top_k=final_k)

    context = "\n\n".join(reranked_chunks)
    return await query_llm_with_context(query, context, chat_history)
