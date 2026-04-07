from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
import asyncio

async def chunk_pages(pages: List[str], chunk_size: int = 900, chunk_overlap: int = 150) -> List[str]:

    full_text = "\n".join(pages)

    if not full_text.strip():
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        separators=[
            "\n\n", # split by paragraphs first
            "\n",   # then by lines
            ". ",  # then by sentences
            "! ",  # then by sentences
            "? ",  # then by sentences
            "; ", # then by sentences
            ", ",  # then by clauses
            " ",   # then by words
            ""    # finally by characters
        ],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    chunks = await asyncio.to_thread(text_splitter.split_text, full_text)

    return chunks