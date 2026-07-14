from src.pdfreader import read_pdf
from src.chunker import chunk_pages
from src.embedder import embed_chunks
from src.vectorstore import store_in_pinecone
from src.corpus_store import save_corpus

async def ingest(pdf_path: str, namespace: str):
    # Step 1: Read PDF
    pages = await read_pdf(pdf_path)

    # Step 2: Chunk Pages
    chunks = await chunk_pages(pages)
    # Step 3: Embed Chunks
    embeddings = await embed_chunks(chunks)

    # Step 4: Store in Pinecone (dense) and keep the full chunk list for BM25 (sparse)
    await store_in_pinecone(chunks, embeddings, namespace=namespace)
    save_corpus(namespace, chunks)
    return len(chunks)

