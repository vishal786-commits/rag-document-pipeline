import os
from pypdf import PdfReader
import asyncio

async def read_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        reader = await asyncio.to_thread(PdfReader, pdf_path)
        pages = [page.extract_text() for page in reader.pages]
        return pages
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []