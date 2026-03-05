from typing import List, Tuple

def chunk_pages(pages: List[str], chunk_size: int = 900, chunk_overlap: int = 150) -> List[str]:
    """
    Chunk the pages into smaller pieces with specified size and overlap.
    
    Args:
        pages (List[str]): List of page texts.
        chunk_size (int): Maximum number of characters in each chunk.
        chunk_overlap (int): Number of overlapping characters between chunks.
        
    Returns:
        List[str]: List of text chunks.
    """
    chunks: List[str] = []

    full_text = "\n".join(pages)
    text_length = len(full_text)

    if text_length == 0:
        return chunks

    start = 0
    while start < text_length:

        end = min(start + chunk_size, text_length)
        chunk = full_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        if end >= text_length:
            break
        start = end - chunk_overlap  # Move back by overlap for the next chunk
        # print("Starting new chunk at index:", start)

    return chunks



