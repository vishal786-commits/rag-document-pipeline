from src.pdfreader import read_pdf
from src.chunker import chunk_pages
from src.embedder import embed_chunks
from src.vectorstore import store_in_pinecone

async def ingest(pdf_path: str, namespace: str):
    # Step 1: Read PDF
    pages = await read_pdf(pdf_path)
    
    # Step 2: Chunk Pages
    chunks = await chunk_pages(pages)
    # Step 3: Embed Chunks
    embeddings = await embed_chunks(chunks)

    # Step 4: Store in Pinecone
    await store_in_pinecone(chunks, embeddings, namespace=namespace)
    return len(chunks)

