from src.pdfreader import read_pdf
from src.chunker import chunk_pages
from src.embedder import embed_chunks
from src.vectorstore import store_in_pinecone
from typing import List

pdf_path = "./data/National Insurance Terms and Conditions for Private Car.pdf"

def ingest():
    # Step 1: Read PDF
    pages = read_pdf(pdf_path)
    
    # Step 2: Chunk Pages
    chunks = chunk_pages(pages)
    # Step 3: Embed Chunks
    embeddings = embed_chunks(chunks)

    # Step 4: Store in Pinecone
    store_in_pinecone(chunks, embeddings, namespace="")

if __name__ == "__main__":
    ingest()