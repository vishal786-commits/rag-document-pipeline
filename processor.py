from pdfreader import read_pdf
from chunker import chunk_pages
from embedder import embed_chunks
from vectorstore import store_in_pinecone
from typing import List

pdf_path = "./resources/The Problem of the Puer Aeternus.pdf"

def run():
    # Step 1: Read PDF
    pages = read_pdf(pdf_path)
    
    # Step 2: Chunk Pages
    chunks = chunk_pages(pages)
    # Step 3: Embed Chunks
    embeddings = embed_chunks(chunks)

    # Step 4: Store in Pinecone
    store_in_pinecone(chunks, embeddings, namespace="")

if __name__ == "__main__":
    run()